# Role-Competency Mapping FastAPI App

A focused FastAPI application that uses Gemini LLM to map organizational roles to competencies from the provided competency framework. The application exposes a single LLM mapping endpoint.

## Features

- FastAPI framework with minimal structure
- Async/await patterns for LLM calls
- Proper error handling and validation
- API documentation with OpenAPI/Swagger
- Role to competency mapping using Gemini LLM
- Structured response with competency relevance scoring

## Project Structure

```
kb-ai-unified-service/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── role_mapping.py    # Role mapping endpoint logic
│   ├── core/
│   │   ├── config.py             # Application configuration
│   │   └── logger.py             # Logging setup
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base.py              # Base Pydantic models
│   │   ├── competency.py        # Competency schemas
│   │   ├── requests.py          # Request schemas
│   │   └── responses.py         # Response schemas
│   └── services/
│       └── gemini_llm.py        # Gemini LLM integration
├── logs/                        # Application logs
├── main.py                     # FastAPI app entry point
├── requirements.txt            # Python dependencies
├── competency_framework.json   # Competency framework data
└── README.md                  # Project documentation
```

## Setup

1. Place your competency framework in `competency_framework.json` in the project root. Use the structure:

```
[
  {
    "name": "Behavioural",
    "competency_theme": [
      {
        "name": "Self-Awareness",
        "competency_sub_theme": [
          "Self-Analysis",
          "Self Confidence",
          "Purposefulness",
          "Self-Learning"
        ]
      }
    ]
  },
  ...
]
```

2. Copy `.env.example` to `.env` and set your Gemini LLM API key and URL.

3. Install dependencies:

```
pip install -r requirements.txt
```

4. Run the app:

```
uvicorn main:app --reload --port 5000
```

5. Test the endpoint at `/docs` (Swagger UI).

## API Format

### Request
```json
{
  "organization": "Ministry of Road Transport and Highways",
  "role_title": "Assistant Executive Engineer Civil",
  "department": "Engineering"  // Optional
}
```

### Response
```json
{
  "organization": "Ministry of Road Transport and Highways",
  "role_title": "Assistant Executive Engineer Civil",
  "mapped_competencies": [
    {
      "category": "Behavioural",
      "theme": "Solution Orientation",
      "sub_themes": ["Analytical Thinking", "Systems Thinking"],
      "relevance": "High"
    }
  ],
  "mapping_rationale": "Brief explanation of why these competencies were selected"
}
```

## Data Models

- **RoleMappingRequest**
  - organization: string
  - role_title: string
  - department: string (optional)

- **CompetencyItem**
  - category: string
  - theme: string
  - sub_themes: string[]
  - relevance: string (Critical/High/Medium/Low)

- **RoleMappingResponse**
  - organization: string
  - role_title: string
  - mapped_competencies: CompetencyItem[]
  - mapping_rationale: string

## Notes
- Only one endpoint is exposed.
- All LLM and framework config is via environment variables.
- Logs are stored in the `logs` directory.
