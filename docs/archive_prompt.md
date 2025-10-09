# Archive Prompt for Master Documentor

## Introduction
The task is to index all files in the `F:\GiljoAI_MCP\docs` directory and its subdirectories. Each file should be described in the existing file `F:\GiljoAI_MCP\docs\index_files.md`.

## Guidelines
- **Format**: Each entry should follow the format:
  ```
  [file name] [current file path] [small 300 word summary] [recommended archive path]
  ```
- **PowerShell Commands**:
  - Use PowerShell commands to research and append content to `index_files.md`.
  - Example command to list files:
    ```powershell
    Get-ChildItem -Path F:\GiljoAI_MCP\docs -Recurse | Select-Object FullName, Name | Format-List
    ```
  - Example command to append content to a file:
    ```powershell
    Add-Content -Path F:\GiljoAI_MCP\docs\index_files.md -Value "file_name.txt F:\GiljoAI_MCP\docs\path\to\file.txt A brief summary of the file here. Recommended archive path: F:\GiljoAI_MCP\docs\archive"
    ```
- **No Deletion**:
  - Do not delete any content already written unless a deletion exceeds 300 words, which requires user permission.
- **Format**: Each entry should follow the format:
  ```
  [file name] [current file path] [small 300 word summary] [recommended archive path]
  ```
- **PowerShell Commands**:
  - Use PowerShell commands to research and append content to `index_files.md`.
  - Example command to list files:
    ```powershell
    Get-ChildItem -Path F:\GiljoAI_MCP\docs -Recurse | Select-Object FullName, Name | Format-List
    ```
  - Example command to append content to a file:
    ```powershell
    Add-Content -Path F:\GiljoAI_MCP\docs\index_files.md -Value "file_name.txt F:\GiljoAI_MCP\docs\path\to\file.txt A brief summary of the file here. Recommended archive path: F:\GiljoAI_MCP\docs\archive"
    ```
- **No Deletion**:
  - Do not delete any content already written unless a deletion exceeds 300 words, which requires user permission.

## Files to Index (58 files total)

### Checklist for Archiving Expert/Librarian
- [ ] Use the provided PowerShell commands to list all files in `F:\GiljoAI_MCP\docs` and its subdirectories.
- [ ] Append descriptions of each file to `index_files.md` following the specified format.
- [ ] Ensure no deletion of content exceeds 300 words without user permission.
- [ ] Verify that all 58 files are described in `F:\GiljoAI_MCP\docs\index_files.md`.
List of all files that need to be indexed. You can use the command provided above to get the list and start appending descriptions to `index_files.md`.

### Example Entry
```
AGENT_INSTRUCTIONS.md F:\GiljoAI_MCP\docs\AGENT_INSTRUCTIONS.md This document provides instructions for agents on how to set up and manage their environment. It includes detailed steps, tips, and best practices for effective agent management. Recommended archive path: F:\GiljoAI_MCP\docs\archive\installation
```

Ensure that all 58 files are described in `F:\GiljoAI_MCP\docs\index_files.md`.
