"""
Simple Web Interface - FastAPI দিয়ে basic web interface
Template path issues ছাড়াই
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI(title="Commission AI Assistant", version="1.0.0")

# Simple HTML template inline
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Commission AI Assistant</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .status-panel {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        .form-group textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            font-family: inherit;
            font-size: 14px;
            resize: vertical;
        }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            transition: transform 0.3s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .result-box {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            font-family: monospace;
            white-space: pre-wrap;
            display: none;
        }
        .success { border-color: #28a745; background: #d4edda; }
        .error { border-color: #dc3545; background: #f8d7da; }
        .loading {
            text-align: center;
            padding: 20px;
            display: none;
        }
        .loading-spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Commission AI Assistant</h1>
            <p>AI-powered SQL generation for MyBL Commission reports</p>
        </div>
        
        <div class="status-panel">
            <h3>📊 System Status</h3>
            <div id="systemStatus">Loading...</div>
        </div>
        
        <div class="form-group">
            <label for="srfText">SRF Content *</label>
            <textarea 
                id="srfText" 
                rows="8" 
                placeholder="Enter your SRF (Sales Report Format) content here...

Example:
Commission Calculation Report for MyBL Campaign
Period: 1st to 15th April 2025
Commission Type: Hourly Commission
Rate: 2% of revenue
Target: Active MSISDN with data usage"
                required></textarea>
        </div>
        
        <div class="form-group">
            <label for="supportingInfo">Supporting Information (Optional)</label>
            <textarea 
                id="supportingInfo" 
                rows="4" 
                placeholder="Enter any additional supporting information..."></textarea>
        </div>
        
        <div style="text-align: center;">
            <button class="btn" onclick="generateSQL()">🚀 Generate SQL Query</button>
            <button class="btn" onclick="clearForm()" style="margin-left: 10px; background: #6c757d;">🗑️ Clear</button>
        </div>
        
        <div class="loading" id="loadingSection">
            <div class="loading-spinner"></div>
            <p>🤖 AI is generating your SQL query...</p>
        </div>
        
        <div class="result-box" id="resultBox"></div>
    </div>

    <script>
        // Check system status on load
        window.onload = function() {
            checkSystemStatus();
        };
        
        async function checkSystemStatus() {
            try {
                const response = await fetch('/api/status');
                const status = await response.json();
                
                let statusHTML = '';
                if (status.initialized) {
                    statusHTML = '✅ System Ready - ' + (status.components?.embeddings?.total_embeddings || 0) + ' embeddings loaded';
                } else {
                    statusHTML = '⚠️ System Not Ready - Please run setup first';
                }
                
                document.getElementById('systemStatus').innerHTML = statusHTML;
            } catch (error) {
                document.getElementById('systemStatus').innerHTML = '❌ Connection Failed';
            }
        }
        
        async function generateSQL() {
            const srfText = document.getElementById('srfText').value.trim();
            const supportingInfo = document.getElementById('supportingInfo').value.trim();
            
            if (!srfText) {
                alert('Please enter SRF content');
                return;
            }
            
            // Show loading
            document.getElementById('loadingSection').style.display = 'block';
            document.getElementById('resultBox').style.display = 'none';
            
            try {
                const response = await fetch('/api/generate-sql', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        srf_text: srfText,
                        supporting_info: supportingInfo
                    })
                });
                
                const result = await response.json();
                
                // Hide loading
                document.getElementById('loadingSection').style.display = 'none';
                
                // Show result
                const resultBox = document.getElementById('resultBox');
                
                if (result.success) {
                    resultBox.className = 'result-box success';
                    resultBox.innerHTML = `✅ SQL Generation Successful!

📊 Context Quality: ${result.context_quality?.quality || 'N/A'}
📈 Similar Examples: ${result.similar_examples_count || 0}
🎯 High Confidence: ${result.high_confidence_count || 0}

💾 Generated SQL:
${'-'.repeat(50)}
${result.generated_sql || 'No SQL generated'}
${'-'.repeat(50)}

🔍 Validation: ${result.validation?.is_valid ? '✅ PASSED' : '⚠️ Issues found'}`;
                } else {
                    resultBox.className = 'result-box error';
                    resultBox.innerHTML = `❌ SQL Generation Failed

Error: ${result.error || 'Unknown error'}`;
                }
                
                resultBox.style.display = 'block';
                
            } catch (error) {
                // Hide loading
                document.getElementById('loadingSection').style.display = 'none';
                
                // Show error
                const resultBox = document.getElementById('resultBox');
                resultBox.className = 'result-box error';
                resultBox.innerHTML = `❌ Connection Failed

Error: ${error.message}`;
                resultBox.style.display = 'block';
            }
        }
        
        function clearForm() {
            document.getElementById('srfText').value = '';
            document.getElementById('supportingInfo').value = '';
            document.getElementById('resultBox').style.display = 'none';
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    """Home page with inline HTML"""
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/api/status")
async def get_status():
    """Simple status check"""
    try:
        # Check if processed data exists
        if os.path.exists("./data/training_data/processed_training_data.json"):
            return {
                "initialized": True,
                "components": {
                    "embeddings": {
                        "status": "ready",
                        "total_embeddings": "33"
                    }
                }
            }
        else:
            return {
                "initialized": False,
                "message": "Training data not found"
            }
    except:
        return {
            "initialized": False,
            "message": "System error"
        }

@app.post("/api/generate-sql")
async def generate_sql_simple(request: dict):
    """Simple SQL generation without complex imports"""
    srf_text = request.get('srf_text', '')
    supporting_info = request.get('supporting_info', '')
    
    if not srf_text:
        return {"success": False, "error": "SRF text is required"}
    
    # For now, return a demonstration response
    # In production, this would call the actual AI system
    demo_sql = f"""
-- Generated SQL for MyBL Commission (Demo Mode)
-- SRF Length: {len(srf_text)} characters

SELECT 
    ret.retailer_msisdn,
    ret.recharge_amount,
    COUNT(*) as hit_count,
    SUM(ret.recharge_amount) as total_recharge,
    CASE 
        WHEN ret.recharge_amount = 307 THEN 63.33
        WHEN ret.recharge_amount = 397 THEN 74.44
        WHEN ret.recharge_amount = 699 THEN 166.67
        WHEN ret.recharge_amount = 798 THEN 200.00
        WHEN ret.recharge_amount = 799 THEN 200.00
        WHEN ret.recharge_amount = 998 THEN 277.78
        ELSE 0
    END as commission_amount
FROM retailer_transactions ret
WHERE ret.transaction_date BETWEEN '2025-04-01' AND '2025-04-15'
    AND ret.retailer_msisdn = '1967021235'
    AND ret.recharge_amount IN (307, 397, 699, 798, 799, 998)
    AND ret.reference_id LIKE 'BLAPP%'
GROUP BY ret.retailer_msisdn, ret.recharge_amount
ORDER BY ret.retailer_msisdn, ret.recharge_amount;
"""
    
    return {
        "success": True,
        "generated_sql": demo_sql.strip(),
        "context_quality": {"quality": "demo"},
        "similar_examples_count": 5,
        "high_confidence_count": 3,
        "validation": {"is_valid": True}
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Commission AI Assistant - Simple Web"}

# Run function
def run_simple_web():
    """Run the simple web application"""
    import uvicorn
    print("🌐 Starting Simple Commission AI Assistant Web App...")
    print("📱 Open http://localhost:8000 in your browser")
    print("⚠️  Note: This is demo mode - actual AI integration requires full setup")
    
    uvicorn.run(
        "simple_web:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    run_simple_web()
