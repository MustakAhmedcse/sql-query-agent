# File Upload Feature for Commission SQL Generator

## Overview

The enhanced UI now supports uploading CSV and Excel files to automatically generate target table schemas for the "Target Tables Structure" text area.

## New Features Added

### 1. File Upload API Endpoints

#### `/upload-files` (POST)

- **Purpose**: Upload CSV/Excel files and generate schema text
- **Input**: Multiple files (CSV, XLSX, XLS)
- **Output**: Schema text for the "Target Tables Structure" text area
- **Response**:
  ```json
  {
    "success": true,
    "schema_text": "TABLE_NAME\nCOLUMN1, TYPE1,\nCOLUMN2, TYPE2,\n...",
    "files_processed": 2
  }
  ```

#### `/generate-sql-with-files` (POST)

- **Purpose**: Process SRF with uploaded files directly
- **Input**: SRF text + files + optional target tables text
- **Output**: Complete SQL generation result

### 2. UI Enhancements

#### New File Upload Section

- **Location**: Above "Target Tables Structure" text area
- **Features**:
  - File type validation (CSV, XLSX, XLS only)
  - Multiple file support
  - Drag & drop styling
  - Auto-population of schema text area

#### Upload Process

1. User selects CSV/Excel files
2. Clicks "Upload & Generate Schema"
3. Files are processed automatically
4. "Target Tables Structure" text area is populated
5. User can edit the generated schema if needed
6. Proceed with normal SQL generation

### 3. Automatic Schema Generation

The system automatically:

- **Reads first sheet** of Excel files
- **Infers column types** from data:
  - Numbers → `NUMBER` or `NUMBER(10,2)`
  - Dates → `DATE`
  - Text → `VARCHAR2(size)` based on content length
- **Cleans column names** (spaces → underscores, uppercase)
- **Creates table names** from filenames

### 4. Example Usage

#### Sample File: `target_data.csv`

```csv
Cluster Name,REGION,DD_CODE,DD Name,SELECTED_REC_TARGET,SELECTED_REC_INCENTIVE
North,Region1,DD001,Distributor A,10000,500
South,Region2,DD002,Distributor B,15000,750
```

#### Generated Schema:

```
TARGET_DATA
CLUSTER_NAME, VARCHAR2(50),
REGION, VARCHAR2(50),
DD_CODE, VARCHAR2(50),
DD_NAME, VARCHAR2(100),
SELECTED_REC_TARGET, NUMBER,
SELECTED_REC_INCENTIVE, NUMBER,
```

## How to Use

### 1. Start the Server

```bash
python api.py
```

### 2. Access the UI

Open `http://localhost:9000` in your browser

### 3. Upload Files

1. Click "Choose Files" in the file upload section
2. Select one or more CSV/Excel files
3. Click "Upload & Generate Schema"
4. The "Target Tables Structure" text area will be populated automatically

### 4. Generate SQL

1. Enter your SRF requirements
2. Review/edit the auto-generated target table structure
3. Click "Generate SQL"

## Testing

### Create Test Files

```bash
python create_test_files.py
```

This creates sample CSV and Excel files in the `test_files` directory for testing.

### Dependencies

Make sure these are installed:

```bash
pip install pandas openpyxl
```

## API Integration

### Frontend JavaScript

The UI uses these key functions:

- `uploadFiles()`: Handles file upload and schema generation
- `generateSQL()`: Original SQL generation (unchanged)

### Backend Processing

- File validation and temporary storage
- Pandas-based schema inference
- Automatic cleanup of temporary files

## Error Handling

The system handles:

- Invalid file types
- Empty files
- File processing errors
- Temporary file cleanup
- User-friendly error messages

## File Type Support

| Format | Extension | Notes                           |
| ------ | --------- | ------------------------------- |
| CSV    | `.csv`    | Standard comma-separated values |
| Excel  | `.xlsx`   | Modern Excel format             |
| Excel  | `.xls`    | Legacy Excel format             |

## Security Considerations

- File type validation
- Temporary file storage with automatic cleanup
- File size limits (can be configured)
- No permanent storage of uploaded files
