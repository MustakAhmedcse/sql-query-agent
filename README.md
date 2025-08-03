# Commission SQL Generator with LangGraph

A sophisticated LLM-powered system for generating step-by-step SQL queries for commission calculations using LangGraph orchestration.

## 🚀 Features

- **LangGraph Orchestration**: Step-by-step workflow with state management
- **LLM-Powered Generation**: Uses OpenAI GPT-4 for intelligent SQL generation
- **Metadata Extraction**: Automatically extracts business rules from SRF documents
- **Modular SQL Steps**: Breaks complex commission logic into manageable steps
- **Comprehensive Reporting**: Detailed generation reports
- **Multiple Interfaces**: CLI, Web API, and programmatic access
- **Production-Ready SQL**: Generates complete, executable SQL scripts

## 📋 Requirements

- Python 3.8+
- OpenAI API key
- Required Python packages (see requirements.txt)

## 🛠️ Installation

1. Clone or download the project
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# .env file
OPENAI_API_KEY=your_openai_api_key_here
```

## 🎯 Usage

### Command Line Interface

#### Generate SQL from SRF requirements:

```bash
# From file
python cli.py generate --srf-file srf_requirements.txt --api-key sk-xxx --output-dir output

# From text
python cli.py generate --srf-text "Commission Name: Test Campaign..." --api-key sk-xxx

# With custom table schemas
python cli.py generate --srf-file srf.txt --schemas-file schemas.json --api-key sk-xxx
```

**Note:** SQL execution has been removed. Use the generated SQL scripts directly in your database client.

### Web API

Start the FastAPI server:

```bash
python api.py
```

Access the web interface at: `http://localhost:9000`

### Programmatic Usage

```python
from orchestrator import CommissionSQLOrchestrator

# Initialize
orchestrator = CommissionSQLOrchestrator(openai_api_key="your_key")

# Process SRF
srf_text = """
Commission Name: Distributor Double Dhamaka Deno Campaign
Start Date: 10-Aug-2024
End Date: 15-Aug-2024
Commission Receiver Channel: Distributor
...
"""

result = orchestrator.process_srf(srf_text)

# Save outputs
orchestrator.save_output(result, "output_directory")
```

## 📊 Generated Output

The system generates the following outputs:

1. **commission_calculation.sql** - Complete SQL script ready for execution
2. **generation_report.md** - Detailed generation report
3. **extracted_metadata.json** - Structured business rules
4. **sql_steps.json** - Individual step details for review

## 🔧 Architecture

### LangGraph Workflow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Extract         │───▶│ Generate SQL    │───▶│ Validate Steps  │
│ Metadata        │    │ Steps           │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Generate        │◀───│ Compile Final   │◀───│                 │
│ Report          │    │ Script          │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### SQL Generation Steps

1. **Setup & Cleaning** - Data preparation and table setup
2. **Mapping Creation** - Agent-to-target mapping tables
3. **KPI Filtering** - Transaction filtering for specific KPIs
4. **Aggregation** - Metric calculation by distributor/retailer
5. **Commission Logic** - Target achievement and bonus calculations
6. **Final Output** - Create summary and detail tables
7. **Validation** - Data quality and summary queries

## 📝 SRF Format

The system expects SRF (Service Request Form) documents with the following information:

```
Commission Name: [Campaign Name]
Start Date: [YYYY-MM-DD]
End Date: [YYYY-MM-DD]
Commission Receiver Channel: [Distributor/Retailer/etc.]

Commission Business Logics:
- KPI: [Type of KPI]
- Target: [Target description]
- Mapping: [Mapping logic]
- Commission Calculation: [Calculation rules]
- Bonus Logic: [Additional incentives]
```

## 🗄️ Database Schema

Required tables:

### EV_RECHARGE_COM_DAILY
- RETAILER_MSISDN (VARCHAR2)
- SUB_MSISDN (VARCHAR2)
- TOP_UP_DATE (DATE)
- RECHARGE_AMOUNT (NUMBER)
- SERVICE_TYPE (VARCHAR2)
- ...

### AGENT_LIST_DAILY
- TOPUP_MSISDN (VARCHAR2)
- RETAILER_CODE (VARCHAR2)
- DIST_CODE (VARCHAR2)
- REGION_NAME (VARCHAR2)
- DATA_DATE (DATE)
- ENABLED (CHAR)
- ...

## 🔍 Example Generated SQL

```sql
-- ========================================================================
-- STEP 1: SETUP_AND_CLEANING
-- Description: Setup and data cleaning operations
-- ========================================================================

-- Clean DD_CODE before joining
UPDATE TEMP_FOR_DENO_CAMP_TAR_15AUG24 SET DD_CODE = TRIM(DD_CODE);
COMMIT;

-- ========================================================================
-- STEP 2: CREATE_MAPPING
-- Description: Create agent-to-target mapping table
-- ========================================================================

CREATE TABLE TEMP_FOR_AG_LIST_MAP_15AUG24 AS
SELECT 
    TAR.*, 
    AG.RETAILER_CODE, 
    AG.TOPUP_MSISDN AS RET_MSISDN
FROM TEMP_FOR_DENO_CAMP_TAR_15AUG24 TAR
JOIN AGENT_LIST_DAILY AG 
    ON AG.DIST_CODE = TAR.DD_CODE 
   AND AG.DATA_DATE = DATE '2024-08-15'
   AND AG.ENABLED = 'Y';

-- ... additional steps
```

## ⚠️ Important Notes

1. **API Key Security**: Never commit API keys to version control
2. **SQL Review**: Always review generated SQL before production use
3. **Database Testing**: Test generated scripts in development environment first
4. **Performance**: Large datasets may require query optimization
5. **Validation**: Validate results after running generated SQL

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the generated reports for error details
2. Validate your SRF format
3. Verify OpenAI API key permissions
4. Review generated SQL before execution
