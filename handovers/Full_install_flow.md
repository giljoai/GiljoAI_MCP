ell 7.5.5

   A new PowerShell stable release is available: v7.6.0
   Upgrade now, or check out the release page at:
     https://aka.ms/PowerShell-Release?tag=v7.6.0

PS C:\Projects\GiljoAI_MCP> python install.py

======================================================================
  GiljoAI MCP - Unified Installer v3.0
======================================================================

Welcome to GiljoAI MCP!
This installer will set up your coding orchestrator.

What will be installed:
  • PostgreSQL database (giljo_mcp)
  • Python dependencies (FastAPI, SQLAlchemy, etc.)
  • Configuration files (.env, config.yaml)
  • API server + Frontend dashboard
  • MCP server integration

Platform: Windows 11
Python: 3.13.7


======================================================================
  Installation Configuration
======================================================================


[Network Configuration]
Configuring external access for frontend connections...

Network access options:
  1. Auto-detect (recommended for development)
     → Dynamically detects IP on each startup
  2. localhost (local access only)
  3. 10.1.0.116 [Wi-Fi]
  4. Enter custom address (domain or IP)

Select network option [1]: 3
[OK] Using 10.1.0.116 [Wi-Fi] for frontend connections

[PostgreSQL Configuration]

PostgreSQL Admin Password Required
This is the password for the 'postgres' superuser account
(The password you set when you first installed PostgreSQL)
Required - no defaults allowed
Password: ****
Confirm password: ****
[OK] Password confirmed

[Post-Installation Options]
Would you like to create desktop shortcuts?
Create shortcuts? (Y/n): y

Configuration Summary:
  • Network mode: Static [Wi-Fi]
  • External access host: 10.1.0.116
  • PostgreSQL password: ******** (secured)
  • Create shortcuts: True

======================================================================
  Checking Python Version
======================================================================

[OK] Python 3.13.7 detected

======================================================================
  Discovering PostgreSQL
======================================================================

[INFO] Checking PATH for psql...
[INFO] Scanning common installation locations...
  Checking: C:\Program Files\PostgreSQL\18\bin\psql.exe
[OK] PostgreSQL detected: C:\Program Files\PostgreSQL\18\bin\psql.exe

======================================================================
  Discovering Node.js
======================================================================

[OK] Node.js detected: C:\Program Files\nodejs\node.EXE (v22.19.0)
[OK] npm detected: C:\Program Files\nodejs\npm.CMD

======================================================================
  Installing Dependencies
======================================================================

[INFO] Creating virtual environment: C:\Projects\GiljoAI_MCP\venv
[OK] Virtual environment created
[INFO] Upgrading pip to latest version...
[!] pip upgrade skipped (non-critical)
[INFO] Installing Python packages (this may take 2-3 minutes)...
You will see pip's progress output below...

Collecting fastapi>=0.100.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 9))
  Downloading fastapi-0.135.2-py3-none-any.whl.metadata (28 kB)
Collecting uvicorn>=0.23.0 (from uvicorn[standard]>=0.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 10))
  Downloading uvicorn-0.42.0-py3-none-any.whl.metadata (6.7 kB)
Collecting pydantic>=2.0.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 11))
  Using cached pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
Collecting sqlalchemy>=2.0.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 14))
  Using cached sqlalchemy-2.0.48-cp313-cp313-win_amd64.whl.metadata (9.8 kB)
Collecting alembic>=1.12.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 15))
  Using cached alembic-1.18.4-py3-none-any.whl.metadata (7.2 kB)
Collecting psycopg2-binary>=2.9.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 16))
  Using cached psycopg2_binary-2.9.11-cp313-cp313-win_amd64.whl.metadata (5.1 kB)
Collecting asyncpg>=0.29.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 17))
  Using cached asyncpg-0.31.0-cp313-cp313-win_amd64.whl.metadata (4.5 kB)
Collecting bcrypt>=4.0.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 20))
  Using cached bcrypt-5.0.0-cp39-abi3-win_amd64.whl.metadata (10 kB)
Collecting cryptography>=42.0.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 21))
  Downloading cryptography-46.0.6-cp311-abi3-win_amd64.whl.metadata (5.7 kB)
Collecting python-multipart>=0.0.6 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 22))
  Using cached python_multipart-0.0.22-py3-none-any.whl.metadata (1.8 kB)
Collecting PyJWT>=2.8.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 23))
  Downloading pyjwt-2.12.1-py3-none-any.whl.metadata (4.1 kB)
Collecting email-validator>=2.1.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 24))
  Using cached email_validator-2.3.0-py3-none-any.whl.metadata (26 kB)
Collecting mcp>=1.23.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Using cached mcp-1.26.0-py3-none-any.whl.metadata (89 kB)
Collecting python-dotenv>=1.0.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 30))
  Using cached python_dotenv-1.2.2-py3-none-any.whl.metadata (27 kB)
Collecting pyyaml>=6.0.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 31))
  Using cached pyyaml-6.0.3-cp313-cp313-win_amd64.whl.metadata (2.4 kB)
Collecting click>=8.1.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 32))
  Using cached click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
Collecting colorama>=0.4.6 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 33))
  Using cached colorama-0.4.6-py2.py3-none-any.whl.metadata (17 kB)
Collecting httpx>=0.25.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 34))
  Using cached httpx-0.28.1-py3-none-any.whl.metadata (7.1 kB)
Collecting aiohttp>=3.9.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 35))
  Downloading aiohttp-3.13.4-cp313-cp313-win_amd64.whl.metadata (8.4 kB)
Collecting websockets>=12.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 36))
  Using cached websockets-16.0-cp313-cp313-win_amd64.whl.metadata (7.0 kB)
Collecting psutil>=5.9.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 37))
  Using cached psutil-7.2.2-cp37-abi3-win_amd64.whl.metadata (22 kB)
Collecting aiofiles>=24.1.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 38))
  Using cached aiofiles-25.1.0-py3-none-any.whl.metadata (6.3 kB)
Collecting tiktoken>=0.5.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 39))
  Using cached tiktoken-0.12.0-cp313-cp313-win_amd64.whl.metadata (6.9 kB)
Collecting structlog>=25.0.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 40))
  Using cached structlog-25.5.0-py3-none-any.whl.metadata (9.5 kB)
Collecting watchdog>=3.0.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 41))
  Using cached watchdog-6.0.0-py3-none-win_amd64.whl.metadata (44 kB)
Collecting sumy>=0.11.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Using cached sumy-0.12.0-py3-none-any.whl.metadata (8.3 kB)
Collecting nltk>=3.8 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 45))
  Downloading nltk-3.9.4-py3-none-any.whl.metadata (3.2 kB)
Collecting numpy>=1.24.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 46))
  Downloading numpy-2.4.3-cp313-cp313-win_amd64.whl.metadata (6.6 kB)
Collecting scipy>=1.10.0 (from -r C:\Projects\GiljoAI_MCP\requirements.txt (line 47))
  Using cached scipy-1.17.1-cp313-cp313-win_amd64.whl.metadata (60 kB)
Collecting starlette>=0.46.0 (from fastapi>=0.100.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 9))
  Downloading starlette-1.0.0-py3-none-any.whl.metadata (6.3 kB)
Collecting typing-extensions>=4.8.0 (from fastapi>=0.100.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 9))
  Using cached typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
Collecting typing-inspection>=0.4.2 (from fastapi>=0.100.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 9))
  Using cached typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
Collecting annotated-doc>=0.0.2 (from fastapi>=0.100.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 9))
  Using cached annotated_doc-0.0.4-py3-none-any.whl.metadata (6.6 kB)
Collecting h11>=0.8 (from uvicorn>=0.23.0->uvicorn[standard]>=0.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 10))
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting annotated-types>=0.6.0 (from pydantic>=2.0.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 11))
  Using cached annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
Collecting pydantic-core==2.41.5 (from pydantic>=2.0.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 11))
  Using cached pydantic_core-2.41.5-cp313-cp313-win_amd64.whl.metadata (7.4 kB)
Collecting greenlet>=1 (from sqlalchemy>=2.0.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 14))
  Using cached greenlet-3.3.2-cp313-cp313-win_amd64.whl.metadata (3.8 kB)
Collecting Mako (from alembic>=1.12.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 15))
  Using cached mako-1.3.10-py3-none-any.whl.metadata (2.9 kB)
Collecting cffi>=2.0.0 (from cryptography>=42.0.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 21))
  Using cached cffi-2.0.0-cp313-cp313-win_amd64.whl.metadata (2.6 kB)
Collecting dnspython>=2.0.0 (from email-validator>=2.1.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 24))
  Using cached dnspython-2.8.0-py3-none-any.whl.metadata (5.7 kB)
Collecting idna>=2.0.0 (from email-validator>=2.1.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 24))
  Using cached idna-3.11-py3-none-any.whl.metadata (8.4 kB)
Collecting anyio>=4.5 (from mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Downloading anyio-4.13.0-py3-none-any.whl.metadata (4.5 kB)
Collecting httpx-sse>=0.4 (from mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Using cached httpx_sse-0.4.3-py3-none-any.whl.metadata (9.7 kB)
Collecting jsonschema>=4.20.0 (from mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Using cached jsonschema-4.26.0-py3-none-any.whl.metadata (7.6 kB)
Collecting pydantic-settings>=2.5.2 (from mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Using cached pydantic_settings-2.13.1-py3-none-any.whl.metadata (3.4 kB)
Collecting pywin32>=310 (from mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Using cached pywin32-311-cp313-cp313-win_amd64.whl.metadata (10 kB)
Collecting sse-starlette>=1.6.1 (from mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Downloading sse_starlette-3.3.3-py3-none-any.whl.metadata (14 kB)
Collecting certifi (from httpx>=0.25.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 34))
  Using cached certifi-2026.2.25-py3-none-any.whl.metadata (2.5 kB)
Collecting httpcore==1.* (from httpx>=0.25.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 34))
  Using cached httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting aiohappyeyeballs>=2.5.0 (from aiohttp>=3.9.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 35))
  Using cached aiohappyeyeballs-2.6.1-py3-none-any.whl.metadata (5.9 kB)
Collecting aiosignal>=1.4.0 (from aiohttp>=3.9.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 35))
  Using cached aiosignal-1.4.0-py3-none-any.whl.metadata (3.7 kB)
Collecting attrs>=17.3.0 (from aiohttp>=3.9.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 35))
  Downloading attrs-26.1.0-py3-none-any.whl.metadata (8.8 kB)
Collecting frozenlist>=1.1.1 (from aiohttp>=3.9.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 35))
  Using cached frozenlist-1.8.0-cp313-cp313-win_amd64.whl.metadata (21 kB)
Collecting multidict<7.0,>=4.5 (from aiohttp>=3.9.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 35))
  Using cached multidict-6.7.1-cp313-cp313-win_amd64.whl.metadata (5.5 kB)
Collecting propcache>=0.2.0 (from aiohttp>=3.9.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 35))
  Using cached propcache-0.4.1-cp313-cp313-win_amd64.whl.metadata (14 kB)
Collecting yarl<2.0,>=1.17.0 (from aiohttp>=3.9.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 35))
  Using cached yarl-1.23.0-cp313-cp313-win_amd64.whl.metadata (82 kB)
Collecting regex>=2022.1.18 (from tiktoken>=0.5.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 39))
  Downloading regex-2026.3.32-cp313-cp313-win_amd64.whl.metadata (41 kB)
Collecting requests>=2.26.0 (from tiktoken>=0.5.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 39))
  Downloading requests-2.33.0-py3-none-any.whl.metadata (5.1 kB)
Collecting breadability>=0.1.20 (from sumy>=0.11.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Using cached breadability-0.1.20-py2.py3-none-any.whl
Collecting docopt-ng>=0.6.1 (from sumy>=0.11.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Using cached docopt_ng-0.9.0-py3-none-any.whl.metadata (13 kB)
Collecting lxml-html-clean (from sumy>=0.11.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Using cached lxml_html_clean-0.4.4-py3-none-any.whl.metadata (2.4 kB)
Collecting pycountry>=18.2.23 (from sumy>=0.11.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Using cached pycountry-26.2.16-py3-none-any.whl.metadata (12 kB)
Collecting setuptools>=65.0.0 (from sumy>=0.11.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Downloading setuptools-82.0.1-py3-none-any.whl.metadata (6.5 kB)
Collecting joblib (from nltk>=3.8->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 45))
  Using cached joblib-1.5.3-py3-none-any.whl.metadata (5.5 kB)
Collecting tqdm (from nltk>=3.8->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 45))
  Using cached tqdm-4.67.3-py3-none-any.whl.metadata (57 kB)
Collecting docopt<0.7,>=0.6.1 (from breadability>=0.1.20->sumy>=0.11.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Using cached docopt-0.6.2-py2.py3-none-any.whl
Collecting chardet (from breadability>=0.1.20->sumy>=0.11.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Downloading chardet-7.4.0.post1-py3-none-any.whl.metadata (8.0 kB)
Collecting lxml>=2.0 (from breadability>=0.1.20->sumy>=0.11.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 44))
  Using cached lxml-6.0.2-cp313-cp313-win_amd64.whl.metadata (3.7 kB)
Collecting pycparser (from cffi>=2.0.0->cryptography>=42.0.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 21))
  Using cached pycparser-3.0-py3-none-any.whl.metadata (8.2 kB)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema>=4.20.0->mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Using cached jsonschema_specifications-2025.9.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema>=4.20.0->mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Using cached referencing-0.37.0-py3-none-any.whl.metadata (2.8 kB)
Collecting rpds-py>=0.25.0 (from jsonschema>=4.20.0->mcp>=1.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 27))
  Using cached rpds_py-0.30.0-cp313-cp313-win_amd64.whl.metadata (4.2 kB)
Collecting charset_normalizer<4,>=2 (from requests>=2.26.0->tiktoken>=0.5.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 39))
  Downloading charset_normalizer-3.4.6-cp313-cp313-win_amd64.whl.metadata (41 kB)
Collecting urllib3<3,>=1.26 (from requests>=2.26.0->tiktoken>=0.5.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 39))
  Using cached urllib3-2.6.3-py3-none-any.whl.metadata (6.9 kB)
Collecting httptools>=0.6.3 (from uvicorn[standard]>=0.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 10))
  Using cached httptools-0.7.1-cp313-cp313-win_amd64.whl.metadata (3.6 kB)
Collecting watchfiles>=0.20 (from uvicorn[standard]>=0.23.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 10))
  Using cached watchfiles-1.1.1-cp313-cp313-win_amd64.whl.metadata (5.0 kB)
Collecting MarkupSafe>=0.9.2 (from Mako->alembic>=1.12.0->-r C:\Projects\GiljoAI_MCP\requirements.txt (line 15))
  Using cached markupsafe-3.0.3-cp313-cp313-win_amd64.whl.metadata (2.8 kB)
Downloading fastapi-0.135.2-py3-none-any.whl (117 kB)
Downloading uvicorn-0.42.0-py3-none-any.whl (68 kB)
Using cached pydantic-2.12.5-py3-none-any.whl (463 kB)
Using cached pydantic_core-2.41.5-cp313-cp313-win_amd64.whl (2.0 MB)
Using cached sqlalchemy-2.0.48-cp313-cp313-win_amd64.whl (2.1 MB)
Using cached alembic-1.18.4-py3-none-any.whl (263 kB)
Using cached psycopg2_binary-2.9.11-cp313-cp313-win_amd64.whl (2.7 MB)
Using cached asyncpg-0.31.0-cp313-cp313-win_amd64.whl (596 kB)
Using cached bcrypt-5.0.0-cp39-abi3-win_amd64.whl (150 kB)
Downloading cryptography-46.0.6-cp311-abi3-win_amd64.whl (3.5 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.5/3.5 MB 44.1 MB/s  0:00:00
Using cached python_multipart-0.0.22-py3-none-any.whl (24 kB)
Downloading pyjwt-2.12.1-py3-none-any.whl (29 kB)
Using cached email_validator-2.3.0-py3-none-any.whl (35 kB)
Using cached mcp-1.26.0-py3-none-any.whl (233 kB)
Using cached python_dotenv-1.2.2-py3-none-any.whl (22 kB)
Using cached pyyaml-6.0.3-cp313-cp313-win_amd64.whl (154 kB)
Using cached click-8.3.1-py3-none-any.whl (108 kB)
Using cached colorama-0.4.6-py2.py3-none-any.whl (25 kB)
Using cached httpx-0.28.1-py3-none-any.whl (73 kB)
Using cached httpcore-1.0.9-py3-none-any.whl (78 kB)
Downloading aiohttp-3.13.4-cp313-cp313-win_amd64.whl (459 kB)
Using cached multidict-6.7.1-cp313-cp313-win_amd64.whl (45 kB)
Using cached yarl-1.23.0-cp313-cp313-win_amd64.whl (87 kB)
Using cached websockets-16.0-cp313-cp313-win_amd64.whl (178 kB)
Using cached psutil-7.2.2-cp37-abi3-win_amd64.whl (137 kB)
Using cached aiofiles-25.1.0-py3-none-any.whl (14 kB)
Using cached tiktoken-0.12.0-cp313-cp313-win_amd64.whl (879 kB)
Using cached structlog-25.5.0-py3-none-any.whl (72 kB)
Using cached watchdog-6.0.0-py3-none-win_amd64.whl (79 kB)
Using cached sumy-0.12.0-py3-none-any.whl (73 kB)
Downloading nltk-3.9.4-py3-none-any.whl (1.6 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.6/1.6 MB 71.2 MB/s  0:00:00
Downloading numpy-2.4.3-cp313-cp313-win_amd64.whl (12.3 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.3/12.3 MB 79.1 MB/s  0:00:00
Using cached scipy-1.17.1-cp313-cp313-win_amd64.whl (36.5 MB)
Using cached aiohappyeyeballs-2.6.1-py3-none-any.whl (15 kB)
Using cached aiosignal-1.4.0-py3-none-any.whl (7.5 kB)
Using cached annotated_doc-0.0.4-py3-none-any.whl (5.3 kB)
Using cached annotated_types-0.7.0-py3-none-any.whl (13 kB)
Downloading anyio-4.13.0-py3-none-any.whl (114 kB)
Downloading attrs-26.1.0-py3-none-any.whl (67 kB)
Using cached cffi-2.0.0-cp313-cp313-win_amd64.whl (183 kB)
Using cached dnspython-2.8.0-py3-none-any.whl (331 kB)
Using cached docopt_ng-0.9.0-py3-none-any.whl (16 kB)
Using cached frozenlist-1.8.0-cp313-cp313-win_amd64.whl (43 kB)
Using cached greenlet-3.3.2-cp313-cp313-win_amd64.whl (230 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Using cached httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Using cached idna-3.11-py3-none-any.whl (71 kB)
Using cached jsonschema-4.26.0-py3-none-any.whl (90 kB)
Using cached jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Using cached lxml-6.0.2-cp313-cp313-win_amd64.whl (4.0 MB)
Using cached propcache-0.4.1-cp313-cp313-win_amd64.whl (40 kB)
Using cached pycountry-26.2.16-py3-none-any.whl (8.0 MB)
Using cached pydantic_settings-2.13.1-py3-none-any.whl (58 kB)
Using cached pywin32-311-cp313-cp313-win_amd64.whl (9.5 MB)
Using cached referencing-0.37.0-py3-none-any.whl (26 kB)
Downloading regex-2026.3.32-cp313-cp313-win_amd64.whl (277 kB)
Downloading requests-2.33.0-py3-none-any.whl (65 kB)
Downloading charset_normalizer-3.4.6-cp313-cp313-win_amd64.whl (154 kB)
Using cached urllib3-2.6.3-py3-none-any.whl (131 kB)
Using cached certifi-2026.2.25-py3-none-any.whl (153 kB)
Using cached rpds_py-0.30.0-cp313-cp313-win_amd64.whl (240 kB)
Downloading setuptools-82.0.1-py3-none-any.whl (1.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 53.5 MB/s  0:00:00
Downloading sse_starlette-3.3.3-py3-none-any.whl (14 kB)
Downloading starlette-1.0.0-py3-none-any.whl (72 kB)
Using cached typing_extensions-4.15.0-py3-none-any.whl (44 kB)
Using cached typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Using cached httptools-0.7.1-cp313-cp313-win_amd64.whl (85 kB)
Using cached watchfiles-1.1.1-cp313-cp313-win_amd64.whl (288 kB)
Downloading chardet-7.4.0.post1-py3-none-any.whl (624 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 624.7/624.7 kB 31.1 MB/s  0:00:00
Using cached joblib-1.5.3-py3-none-any.whl (309 kB)
Using cached lxml_html_clean-0.4.4-py3-none-any.whl (14 kB)
Using cached mako-1.3.10-py3-none-any.whl (78 kB)
Using cached markupsafe-3.0.3-cp313-cp313-win_amd64.whl (15 kB)
Using cached pycparser-3.0-py3-none-any.whl (48 kB)
Using cached tqdm-4.67.3-py3-none-any.whl (78 kB)
Installing collected packages: pywin32, docopt, websockets, watchdog, urllib3, typing-extensions, structlog, setuptools, rpds-py, regex, pyyaml, python-multipart, python-dotenv, PyJWT, pycparser, pycountry, psycopg2-binary, psutil, propcache, numpy, multidict, MarkupSafe, lxml, joblib, idna, httpx-sse, httptools, h11, greenlet, frozenlist, docopt-ng, dnspython, colorama, charset_normalizer, chardet, certifi, bcrypt, attrs, asyncpg, annotated-types, annotated-doc, aiohappyeyeballs, aiofiles, yarl, typing-inspection, tqdm, sqlalchemy, scipy, requests, referencing, pydantic-core, Mako, lxml-html-clean, httpcore, email-validator, click, cffi, breadability, anyio, aiosignal, watchfiles, uvicorn, tiktoken, starlette, pydantic, nltk, jsonschema-specifications, httpx, cryptography, alembic, aiohttp, sumy, sse-starlette, pydantic-settings, jsonschema, fastapi, mcp
Successfully installed Mako-1.3.10 MarkupSafe-3.0.3 PyJWT-2.12.1 aiofiles-25.1.0 aiohappyeyeballs-2.6.1 aiohttp-3.13.4 aiosignal-1.4.0 alembic-1.18.4 annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.13.0 asyncpg-0.31.0 attrs-26.1.0 bcrypt-5.0.0 breadability-0.1.20 certifi-2026.2.25 cffi-2.0.0 chardet-7.4.0.post1 charset_normalizer-3.4.6 click-8.3.1 colorama-0.4.6 cryptography-46.0.6 dnspython-2.8.0 docopt-0.6.2 docopt-ng-0.9.0 email-validator-2.3.0 fastapi-0.135.2 frozenlist-1.8.0 greenlet-3.3.2 h11-0.16.0 httpcore-1.0.9 httptools-0.7.1 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 joblib-1.5.3 jsonschema-4.26.0 jsonschema-specifications-2025.9.1 lxml-6.0.2 lxml-html-clean-0.4.4 mcp-1.26.0 multidict-6.7.1 nltk-3.9.4 numpy-2.4.3 propcache-0.4.1 psutil-7.2.2 psycopg2-binary-2.9.11 pycountry-26.2.16 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.13.1 python-dotenv-1.2.2 python-multipart-0.0.22 pywin32-311 pyyaml-6.0.3 referencing-0.37.0 regex-2026.3.32 requests-2.33.0 rpds-py-0.30.0 scipy-1.17.1 setuptools-82.0.1 sqlalchemy-2.0.48 sse-starlette-3.3.3 starlette-1.0.0 structlog-25.5.0 sumy-0.12.0 tiktoken-0.12.0 tqdm-4.67.3 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uvicorn-0.42.0 watchdog-6.0.0 watchfiles-1.1.1 websockets-16.0 yarl-1.23.0

[notice] A new release of pip is available: 25.2 -> 26.0.1
[notice] To update, run: C:\Projects\GiljoAI_MCP\venv\Scripts\python.exe -m pip install --upgrade pip
[OK] Dependencies installed successfully
[INFO] Setting up pre-commit hooks...
[OK] Pre-commit hooks installed
[INFO] Downloading NLTK data for vision summarization...
[OK] NLTK data downloaded successfully

======================================================================
  Generating Configuration Files
======================================================================

[INFO] Generating config.yaml...
[OK] Configuration file generated (config.yaml)

======================================================================
  Setting Up Database
======================================================================

[INFO] Creating database and roles...
[OK] Database and roles created successfully
[INFO] Generating .env with real database credentials...
[INFO] Regenerating .env with real database passwords...
[OK] Configuration updated with database credentials
[OK] .env file generated with database credentials
[INFO] Loaded DATABASE_URL from .env: postgresql://giljo_user:W6mcN0qRydn5bpjj1dDW@...
[INFO] Running database migrations to create schema...
[INFO] Fresh install detected - will run baseline migration
[INFO] Running database migrations (alembic upgrade head)...
[OK] Database migrations completed successfully
[INFO] No new migrations to apply (database already up to date)
[INFO] Verifying database schema...
Using proactor: IocpProactor
[OK] Schema verified: 7 essential tables present
[OK] Database schema created via Alembic migrations
[INFO] Creating setup state...
Using proactor: IocpProactor
[OK] Setup state initialized
[INFO] Seeding demo data for agent succession...
Using proactor: IocpProactor
[OK] Demo data seeded successfully

======================================================================
  Applying Database Migrations
======================================================================

Using proactor: IocpProactor
[INFO] Upgrading migration chain: 0840e_project_meta -> baseline_v33
[INFO] Reconciling schema for baseline_v33...
[OK] Schema reconciled and stamped to baseline_v33
[INFO] Running database migrations (alembic upgrade head)...
[OK] Database migrations completed successfully
[INFO] No new migrations to apply (database already up to date)
[INFO] Verifying database schema...
Using proactor: IocpProactor
[OK] Schema verified: 7 essential tables present
[INFO] Seeding demo data for agent succession...
Using proactor: IocpProactor
[OK] Demo data seeded successfully

======================================================================
  Installing Frontend Dependencies
======================================================================

[INFO] Installing frontend dependencies...
[INFO] Running npm pre-flight checks...
[INFO] Installing frontend dependencies...
[INFO] Verifying installation integrity...
[OK] Frontend dependencies installed and verified successfully
[OK] Frontend dependencies installed successfully

======================================================================
  HTTPS Configuration (Optional)
======================================================================


HTTPS encrypts all traffic between your browser and GiljoAI.
Uses mkcert to generate locally-trusted certificates (no browser warnings).
Note: Some CLI tools (Gemini CLI) require extra certificate trust
configuration with self-signed HTTPS. HTTP is recommended for local/LAN use.
You can always enable HTTPS later from Admin Settings > Network.

Enable HTTPS? [y/N]: n
[INFO] Skipping HTTPS — can be enabled later from Admin Settings > Network

======================================================================
  Creating Desktop Shortcuts
======================================================================

[OK] Created shortcut: C:\Users\PatrikPettersson\OneDrive - GiljoAi\Desktop\GiljoAI MCP.lnk
[OK] Created shortcut: C:\Users\PatrikPettersson\OneDrive - GiljoAi\Desktop\Stop GiljoAI.lnk

============================================================
  Installation Complete!
============================================================

Database: giljo_mcp @ localhost:5432 (owner: giljo_owner, user: giljo_user)

Start the application:
  python startup.py

Then open your browser:
  http://localhost:7274
  http://10.1.0.116:7274  (LAN)

API docs: http://localhost:7272/docs

Create your administrator account on first visit.

PS C:\Projects\GiljoAI_MCP> python startup --verbose
C:\Python313\python.exe: can't open file 'C:\\Projects\\GiljoAI_MCP\\startup': [Errno 2] No such file or directory
PS C:\Projects\GiljoAI_MCP> python startup.py --verbose
Re-launching GiljoAI MCP startup inside project virtual environment...

======================================================================
  GiljoAI MCP - Unified Startup v3.0
======================================================================


======================================================================
  Checking Dependencies
======================================================================

[INFO] Checking Python Version...
[OK] Python 3.13.7 detected
[INFO] Checking PostgreSQL...
[OK] PostgreSQL detected at: C:\Program Files\PostgreSQL\18\bin\psql.exe
[!] PostgreSQL not in PATH - consider adding to environment variables
[INFO] Checking pip...
[OK] pip detected at: C:\Python313\Scripts\pip.EXE
[INFO] Checking npm (optional)...
[OK] npm detected at: C:\Program Files\nodejs\npm.CMD

======================================================================
  Installing Requirements
======================================================================

[INFO] Checking if requirements are already installed...
[OK] Requirements already installed

======================================================================
  Downloading NLTK Data
======================================================================

[OK] NLTK punkt tokenizer already downloaded

======================================================================
  Running Database Migrations
======================================================================

[OK] Database migrations successful

======================================================================
  Database Connectivity
======================================================================

[INFO] Checking database connection...
[OK] Database connection successful

======================================================================
  Setup Status
======================================================================

[INFO] Checking setup completion status...
[OK] Setup completed previously - launching dashboard

======================================================================
  Port Availability
======================================================================

[INFO] Checking API port 7272...
[INFO] Checking frontend port 7274...

======================================================================
  Starting Services
======================================================================

[INFO] Verbose mode enabled - services will open in separate console windows
[INFO] Starting API server...
[OK] API server will open in new console window
[OK] API server started (PID: 3088)
[INFO] Starting frontend server...
[OK] Frontend server will open in new console window
[OK] Frontend server started (PID: 11872)

======================================================================
  Waiting for Services
======================================================================

[INFO] Waiting for API to be ready (max 30s)...
