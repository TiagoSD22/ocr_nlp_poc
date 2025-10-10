# Certificate OCR Extraction API

Uma aplicação Flask para extração automática de informações de certificados usando OCR (Tesseract) e análise semântica com sentence-transformers.

## Funcionalidades

- **OCR Avançado**: Extração de texto de documentos PDF, PNG, JPEG e outros formatos
- **Análise Semântica**: Identificação inteligente de campos específicos usando vetorização semântica
- **API REST**: Endpoint simples para upload e processamento de documentos
- **Suporte Multi-formato**: Conversão automática de PDF para imagem
- **Containerização**: Dockerfile incluído para deploy fácil

## Campos Extraídos

A aplicação identifica automaticamente os seguintes campos em certificados:

- **Nome do Participante**: Nome completo da pessoa certificada
- **Evento**: Nome do curso, workshop, seminário ou treinamento
- **Local**: Cidade, endereço ou localização do evento
- **Data**: Data de realização ou período do evento
- **Carga Horária**: Duração total em horas

## Tecnologias Utilizadas

- **Flask**: Framework web Python
- **Tesseract OCR**: Engine de reconhecimento óptico de caracteres
- **Sentence Transformers**: Modelo de IA para análise semântica
- **PIL/Pillow**: Processamento de imagens
- **pdf2image**: Conversão de PDF para imagem
- **scikit-learn**: Cálculo de similaridade coseno

## Instalação e Uso

### Usando Docker (Recomendado)

```bash
# Build da imagem
docker build -t certificate-ocr .

# Executar container
docker run -p 5000:5000 certificate-ocr
```

### Instalação Local

1. Instalar dependências do sistema:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng poppler-utils

# macOS (com Homebrew)
brew install tesseract poppler
```

2. Instalar dependências Python:
```bash
pip install -r requirements.txt
```

3. Executar aplicação:
```bash
python app.py
```

## Uso da API

### Health Check

```bash
GET /health
```

### Extração de Certificado

```bash
POST /extract-certificate
Content-Type: multipart/form-data
```

**Parâmetros:**
- `file`: Arquivo do certificado (PDF, PNG, JPEG, etc.)

**Exemplo usando curl:**
```bash
curl -X POST -F "file=@certificado.pdf" http://localhost:5000/extract-certificate
```

## Configuração

### Limites

- **Tamanho máximo do arquivo**: 16MB
- **Formatos suportados**: PDF, PNG, JPG, JPEG, TIFF, BMP
- **Timeout**: 120 segundos para processamento

## Licença

Este projeto está sob a licença MIT.
