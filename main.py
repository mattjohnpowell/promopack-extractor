from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
import httpx
import fitz  # PyMuPDF
import langextract as lx
from typing import List
import os
import textwrap

app = FastAPI(title="PromoPack Claim Extractor", version="1.0")

# Security
security = HTTPBearer()

# Environment variables
API_KEY_SECRET = os.getenv("API_KEY_SECRET", "default-secret-key")  # Change in production

# Models
class ExtractClaimsRequest(BaseModel):
    document_url: HttpUrl

class Claim(BaseModel):
    text: str
    page: int
    confidence_score: float

class ExtractClaimsResponse(BaseModel):
    claims: List[Claim]

# Authentication dependency
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@app.post("/extract-claims", response_model=ExtractClaimsResponse)
async def extract_claims(request: ExtractClaimsRequest, api_key: str = Depends(verify_api_key)):
    try:
        # Download PDF
        async with httpx.AsyncClient() as client:
            response = await client.get(str(request.document_url), timeout=30.0)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to download document")
            
            pdf_bytes = response.content
            if len(pdf_bytes) > 20 * 1024 * 1024:  # 20MB limit
                raise HTTPException(status_code=400, detail="Document too large")

        # Extract text from PDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if not doc:
            raise HTTPException(status_code=422, detail="Invalid PDF document")
        
        pages_text = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            pages_text.append((page_num + 1, text))  # page numbers start from 1
        
        doc.close()

        # Concatenate all text for extraction
        full_text = "\n".join([text for _, text in pages_text])

        # Define extraction prompt and examples for claims
        prompt = textwrap.dedent("""\
            Extract key claims from the document. A claim is a significant statement that asserts facts about results, efficacy, or findings.
            Extract the exact text of the claim without paraphrasing.""")
        
        examples = [
            lx.data.ExampleData(
                text="The study showed that Drug X reduced symptoms by 50% compared to placebo.",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="claim",
                        extraction_text="The study showed that Drug X reduced symptoms by 50% compared to placebo",
                        attributes={"confidence": 0.95}
                    )
                ]
            ),
            lx.data.ExampleData(
                text="Patients treated with the new therapy had a 30% improvement in quality of life.",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="claim",
                        extraction_text="Patients treated with the new therapy had a 30% improvement in quality of life",
                        attributes={"confidence": 0.92}
                    )
                ]
            )
        ]

        # Extract claims using LangExtract
        result = lx.extract(
            text_or_documents=full_text,
            prompt_description=prompt,
            examples=examples,
            model_id="gemini-2.5-flash"
        )

        # Process extractions
        claims = []
        for extraction in result.extractions:
            claim_text = extraction.extraction_text
            confidence = extraction.attributes.get("confidence", 0.9)
            
            # Find the page where this claim appears
            page_num = None
            for p_num, p_text in pages_text:
                if claim_text in p_text:
                    page_num = p_num
                    break
            if page_num:
                claims.append(Claim(text=claim_text, page=page_num, confidence_score=confidence))

        return ExtractClaimsResponse(claims=claims)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)