# slidespeak-backend

![slidespeak-banner-github](https://github.com/SlideSpeak/slidespeak-backend/assets/5519740/431c46b2-1030-429b-b06c-e4844983de5b)

SlideSpeak allows you to chat with your PowerPoint slides. Upload any PPTX file and ask questions about the content.

SlideSpeak was built with:

- [Llama Index](https://github.com/jerryjliu/llama_index) and uses the OpenAI [GPT 3.5 Turbo](https://platform.openai.com/docs/models/gpt-3-5) Mobel
- [PineCone](https://www.pinecone.io/) as the primary vector storage
- [MongoDB](https://mongodb.com/) as the Index Store and Document Store
- AWS S3 as the blob file storage

The frontend for this project is available here: [https://github.com/SlideSpeak/slidespeak-webapp](https://github.com/SlideSpeak/slidespeak-webapp)

## Requirements

- Python3
- Pinecone
- MongoDB
- S3 with AWS credentials
- OpenAI API credentials

## Installation

- Create a virtual env: `python3 -m venv env`
- Activate the virtual env: `source env/bin/activate`
- Install all dependencies `python3 -m pip install -r requirements.txt`
- Enable python cerificate: `sudo /Applications/Python[VERSION]/Certificates.command`
- Install unoconv: `brew install unoconv`
- Install libreoffice via `https://libreoffice.org/download/`
- Create `.env` and set all environment variables (see `.env.example`)

## Setup

_Please note:_ Both the index server and the flask backend need to run in parallel.

- Start index server `python3 index_server.py`
- Start Flask Backend `python3 flask_demo.py`

## License

See LICENSE file.
