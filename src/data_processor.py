"""
Data Processor - আপনার SRF-SQL pairs process করার জন্য
Simple এবং easy to understand
Enhanced with metadata extraction
"""
import json
import os
import pandas as pd
import re
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """SRF-SQL data process করার জন্য simple class"""
    
    def __init__(self, data_path="./data/training_data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
    def load_existing_data(self, jsonl_file_path):
        """
        আপনার existing srf_sql_pairs.jsonl file load করে
        """
        try:
            data = []
            logger.info(f"Loading data from: {jsonl_file_path}")
            
            with open(jsonl_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():  # Empty line skip করি
                        item = json.loads(line)
                        data.append(item)
            
            logger.info(f"Loaded {len(data)} SRF-SQL pairs")
            return data            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return []
    
    def clean_and_process_data(self, data):
        """
        Data clean করে processed format এ convert করি এবং মেটাডাটা এক্সট্র্যাক্ট করি
        """
        processed_data = []
        
        for item in data:
            try:
                # Basic cleaning
                srf_text = self._clean_text(item.get('srf', ''))
                sql_query = self._clean_sql(item.get('sql', ''))
                supporting_table = item.get('supporting_table', '')
                
                # Skip empty data
                if not srf_text or not sql_query:
                    continue
                
                # মেটাডাটা এক্সট্র্যাক্ট করি
                metadata = self.extract_commission_metadata(srf_text)
                
                processed_item = {
                    'id': len(processed_data) + 1,
                    'srf_text': srf_text,
                    'sql_query': sql_query,
                    'supporting_table': supporting_table,
                    'srf_length': len(srf_text),
                    'sql_length': len(sql_query),
                    'commission_name': metadata['commission_name'],
                    'commission_type': metadata['commission_type']
                }
                
                processed_data.append(processed_item)
                
            except Exception as e:
                logger.warning(f"Error processing item: {str(e)}")
                continue
        
        # Categorize data
        processed_data = self.categorize_data_by_metadata(processed_data)
        
        logger.info(f"Processed {len(processed_data)} valid items")
        return processed_data
    
    def _clean_text(self, text):
        """Text clean করার simple function"""
        if not text:
            return ""
        
        # Basic cleaning
        text = str(text).strip()
        # Remove extra spaces
        text = ' '.join(text.split())
        # Remove special characters that might cause issues
        text = text.replace('\x00', '').replace('\r', '\n')
        
        return text
    
    def _clean_sql(self, sql):
        """SQL clean করার function"""
        if not sql:
            return ""
        
        sql = str(sql).strip()
        # Basic SQL formatting
        sql = sql.replace('\r\n', '\n').replace('\r', '\n')
        
        return sql
    
    def save_processed_data(self, processed_data, filename="processed_training_data.json"):
        """Processed data save করি"""
        try:
            output_path = self.data_path / filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Saved processed data to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            return None
    
    def get_data_statistics(self, data):
        """Data এর basic statistics"""
        if not data:
            return {}
        
        stats = {
            'total_items': len(data),
            'avg_srf_length': sum(item['srf_length'] for item in data) / len(data),
            'avg_sql_length': sum(item['sql_length'] for item in data) / len(data),
            'min_srf_length': min(item['srf_length'] for item in data),
            'max_srf_length': max(item['srf_length'] for item in data)
        }
        
        return stats
    
    def extract_commission_metadata(self, srf_text):
        """
        SRF থেকে কমিশন টাইপ এবং নাম এক্সট্র্যাক্ট করে
        """
        commission_name = None
        commission_type = None
        
        try:
            # রিপোর্ট টাইটেল এক্সট্র্যাক্ট করি
            report_title_pattern = r"Report Title:\s*(.+?)(?:\r|\n)"
            report_title_match = re.search(report_title_pattern, srf_text)
            
            if report_title_match:
                commission_name = report_title_match.group(1).strip()
                
                # উন্নত ফাংশন ব্যবহার করে কমিশন টাইপ এক্সট্র্যাক্ট করি
                commission_type = self._extract_commission_type(commission_name)
                
        except Exception as e:
            logger.warning(f"Error extracting metadata: {str(e)}")
        
        return {
            "commission_name": commission_name or "unknown",
            "commission_type": commission_type or "unknown"
        }
    
    def _extract_commission_type(self, commission_name):
        """
        বিভিন্ন ফরম্যাটের কমিশন নাম থেকে কমিশন টাইপ এক্সট্র্যাক্ট করে
        """
        if not commission_name:
            return "unknown"
            
        # স্টেপ 1: ডেট প্যাটার্ন খুঁজে বের করি
        date_patterns = [
            r'_\d+(?:st|nd|rd|th)?\s+(?:to|and)\s+\d+(?:st|nd|rd|th)?\s+[A-Za-z]+\'?\d+',  # _11th to 12th May22
            r'_\d+(?:st|nd|rd|th)?\s+[A-Za-z]+\'?\d+\s+to\s+\d+(?:st|nd|rd|th)?\s+[A-Za-z]+\'?\d+', # _1st Apr25 to 15th Apr25
            r'\d+(?:st|nd|rd|th)?\s+to\s+\d+(?:st|nd|rd|th)?\s+[A-Za-z]+\'?\d+', # 11th to 12th May22
            r'\d+(?:st|nd|rd|th)?\s+[A-Za-z]+\'?\d+', # 11th Apr22
            r'[A-Za-z]+\'?\d+', # May22, Apr'25
        ]
        
        commission_type = commission_name
        
        # ডেট প্যাটার্নগুলি খুঁজি
        for pattern in date_patterns:
            match = re.search(pattern, commission_type)
            if match:
                # ডেট এবং তার আগের '_' রিমুভ করি
                date_part = match.group(0)
                if date_part.startswith('_'):
                    date_part = date_part
                else:
                    date_part = f" {date_part}"
                commission_type = commission_type.replace(date_part, '')
                break
        
        # স্টেপ 2: শেষের অতিরিক্ত '_' রিমুভ করি
        commission_type = commission_type.rstrip('_')
        
        # স্টেপ 3: স্পেশাল কেস হ্যান্ডল করি
        if commission_type.startswith("Commission for "):
            # "Commission for Nagad" এর ক্ষেত্রে পুরো নামই রাখি
            return commission_type.strip()
        
        # স্টেপ 4: MyBL Hourly, Portonics ইত্যাদি প্যাটার্ন হ্যান্ডল করি
        if "MyBL" in commission_type and "Hourly" in commission_type:
            if "Portonics" in commission_type:
                return "MyBL Hourly Portonics"
            return "MyBL Hourly"
        
        if "BP Variable Incentive" in commission_type:
            return "BP Variable Incentive"
        
        # স্টেপ 5: তবুও যদি '_' থাকে তবে সবগুলো রাখি (RSO_RSO Supervisor_BP_GA ক্ষেত্রে)
        if "_" in commission_type and any(x in commission_type for x in ["RSO", "BP", "GA"]):
            return commission_type.strip()
        
        return commission_type.strip()

    def categorize_data_by_metadata(self, processed_data):
        """
        Add categories to data for better filtering
        """
        for item in processed_data:
            srf_text = item['srf_text'].lower()
            
            # Categorize by commission type
            if 'hourly' in srf_text:
                item['sub_category'] = 'hourly'
            elif 'special day' in srf_text:
                item['sub_category'] = 'special_day'
            elif 'regular' in srf_text:
                item['sub_category'] = 'regular'
            else:
                item['sub_category'] = 'other'
                
            # Extract supporting tables info
            if item.get('supporting_table'):
                item['has_supporting_table'] = True
                item['table_info'] = self._extract_table_info(item['supporting_table'])
            else:
                item['has_supporting_table'] = False
                item['table_info'] = {}
        
        return processed_data
    
    def _extract_table_info(self, supporting_table):
        """Extract supporting tables and organize structured data"""
        table_info = {
            'columns': [],
            'row_count': 0,
            'has_deno': False,
            'has_commission': False
        }
        
        try:
            # Parse CSV data
            import io
            import pandas as pd
            csv_data = io.StringIO(supporting_table)
            df = pd.read_csv(csv_data)
            
            # Extract key columns
            table_info['columns'] = df.columns.tolist()
            table_info['row_count'] = len(df)
            
            # Check for important columns
            column_names = [col.upper() for col in df.columns]
            table_info['has_deno'] = any('DENO' in col for col in column_names)
            table_info['has_commission'] = any('COMMISSION' in col for col in column_names)
            
        except Exception as e:
            logger.warning(f"Could not parse supporting table: {e}")
            
        return table_info

# Usage example function
def process_your_data(jsonl_file_path):
    """
    আপনার data process করার জন্য main function
    """
    print("🚀 Starting data processing...")
    
    # Data processor তৈরি করি
    processor = DataProcessor()
    
    # আপনার existing data load করি
    raw_data = processor.load_existing_data(jsonl_file_path)
    
    if not raw_data:
        print("❌ No data found to process")
        return None
    
    # Data clean ও process করি
    processed_data = processor.clean_and_process_data(raw_data)
    
    # Statistics দেখি
    stats = processor.get_data_statistics(processed_data)
    print("\n📊 Data Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Processed data save করি
    saved_path = processor.save_processed_data(processed_data)
    
    if saved_path:
        print(f"✅ Data processing completed! Saved to: {saved_path}")
        return processed_data
    else:
        print("❌ Failed to save processed data")
        return None

# Direct run করার জন্য
if __name__ == "__main__":
    # আপনার existing data file path
    your_jsonl_file = "../MyBL_FEB_MAR_APR_MAY_25/srf_sql_pairs.jsonl"
    
    # Process করি
    result = process_your_data(your_jsonl_file)
    
    if result:
        print(f"\n🎉 Successfully processed {len(result)} SRF-SQL pairs!")
    else:
        print("\n😔 Data processing failed!")
