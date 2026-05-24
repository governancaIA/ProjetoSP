# EPIC 1: Ingestão e Parsing de Arquivos Fiscais — Decomposição Detalhada

**Status:** 🔲 Não iniciada  
**Prioridade:** MVP  
**Estimativa:** G (25–30 dias)  
**Data Planejada:** Sprint 1–2  

---

## 🎯 Objetivo & Valor

**Negócio:** Eliminar processo manual de importação de arquivos fiscais (SPED EFD, XML NF-e, CT-e, etc).  
**Valor:** Cliente importa meses de histórico fiscal em minutos, com garantia de integridade.  
**Métrica de Sucesso:** <30s para importar 100 NFs; detecção de tipo/versão >99% acurada.

---

## 📋 User Stories

### US-1.1: Upload via UI (Drag-and-Drop)

**Como** usuário fiscal,  
**Quero** fazer upload de arquivos (SPED, XML) via interface web (drag-and-drop),  
**Para que** não precise usar linha de comando ou FTP.

**AC:**
- [ ] Interface aceita drag-and-drop de múltiplos arquivos
- [ ] Exibe progresso em tempo real (% de upload)
- [ ] Validação de extensão (`.txt`, `.xml`, `.zip`)
- [ ] Aceita até 2 GB por arquivo
- [ ] Checksum SHA-256 calculado no cliente; validado no servidor
- [ ] Mensagem de erro clara se arquivo inválido ou duplicado

**Dependências:** EPIC 7 (auth), EPIC 8 (storage backend)  
**Complexidade:** M  
**Estimativa:** 3–4 dias  

---

### US-1.2: Upload via API REST (Lotes)

**Como** sistema integrado (ERP),  
**Quero** enviar arquivos via API REST com suporte a lotes,  
**Para que** integração programática seja viável.

**AC:**
- [ ] Endpoint `POST /api/v1/uploads` aceita `multipart/form-data`
- [ ] Suporta até 10 arquivos por request
- [ ] Retorna `job_id` para tracking assíncrono
- [ ] Suporta `.zip` contendo múltiplos arquivos SPED/XML
- [ ] Rate limiting: básico (10 uploads/dia), pro (100), enterprise (ilimitado)
- [ ] Resposta inclui `job_id`, `status`, `webhook_url` (opcional)

**Dependências:** EPIC 8, EPIC 7  
**Complexidade:** M  
**Estimativa:** 3–4 dias  

---

### US-1.3: Detecção Automática de Tipo e Versão

**Como** sistema de processamento,  
**Quero** detectar automaticamente se é SPED EFD, EFD Contrib, NF-e, CT-e,  
**Para que** rota para parser correto sem input manual.

**AC:**
- [ ] Lê header e estrutura de arquivo
- [ ] SPED EFD ICMS: detecta bloco `0|ID`, `0|FIN`, `0|ICP`
- [ ] EFD Contribuições: detecta marca `EFD1E`, `M100`
- [ ] NF-e XML: detecta tag `<NFe>` e schema v4.0
- [ ] CT-e XML: detecta tag `<CTe>` e schema v3.0
- [ ] Acurácia: >99% para casos normais; warnings para ambíguos
- [ ] Versão do schema extraída (ex: `SPED v10.0.0`)

**Dependências:** US-1.1, US-1.2  
**Complexidade:** M  
**Estimativa:** 2–3 dias  

---

### US-1.4: Parser de SPED EFD ICMS/IPI

**Como** motor de validação,  
**Quero** extrair registros C100, C170, D100, E110 do SPED EFD,  
**Para que** dados estruturados alimentem regras e scoring.

**AC:**
- [ ] Parse linha-por-linha do SPED (UTF-8, separador `|`)
- [ ] Extrai e estrutura:
  - `C100`: cabeçalho NF-e (chave, emitente, data, valor)
  - `C170`: itens NF-e (CFOP, NCM, qtd, valor, impostos)
  - `D100`: cabeçalho CT-e
  - `E110`: apuração ICMS (base, alíquota, valor)
- [ ] Registros desconhecidos logados como warnings (não falha)
- [ ] Relaciona C100 ↔ C170 por ordem de aparição
- [ ] Trata diferimentos e isenções (CST 00, 10, 20, 30, 40, 41, 50, 51, 60, 70, 90)
- [ ] Valida tipos de dados (datas ISO, valores com 2 decimais)
- [ ] Output JSON normalizado com metadata (versão SPED, período, CNPJ emitente)

**Dependências:** US-1.3, EPIC 7 (tenant_id)  
**Complexidade:** G  
**Estimativa:** 5–7 dias  

---

### US-1.5: Parser de EFD Contribuições (PIS/COFINS)

**Como** motor de validação,  
**Quero** extrair registros M100, M200, M400, M500 da EFD Contribuições,  
**Para que** regras de PIS/COFINS por CST funcionem.

**AC:**
- [ ] Parse da EFD Contribuições (blocos 0, A, C, D, F, M, P, 1)
- [ ] Extrai:
  - `M100`: detalhamento de receitas por CST
  - `M200`: detalhamento de deduções
  - `M400`: detalhamento de COFINS
  - `M500`: consolidação por tipo de receita
- [ ] Relaciona M100 ↔ M200 por períodos
- [ ] Calcula PIS/COFINS esperado vs declarado
- [ ] Detecta CST inválidos para regime tributário
- [ ] Output JSON com estrutura espelhada SPED ICMS

**Dependências:** US-1.4  
**Complexidade:** M  
**Estimativa:** 4–5 dias  

---

### US-1.6: Parser de NF-e XML (Schema v4.0)

**Como** motor de validação,  
**Quero** extrair dados de NF-e XML (chave, emitente, itens, impostos, protocolo),  
**Para que** compare com dados SPED.

**AC:**
- [ ] Parse XML com validação de schema XSD v4.0
- [ ] Extrai:
  - Chave de acesso (forma: 35 dígitos)
  - CNPJ/CPF emitente e destinatário
  - Data de emissão e saída
  - Natureza (saída, devolução, complementar, ajuste)
  - Itens: código, descrição, CFOP, NCM, ICMS, PIS, COFINS, IPI
  - Totais: valor produtos, frete, desconto, impostos
  - Status: autorizado, cancelado (evento 110111), denegado
  - Protocolo de autorização (data, SEFAZ)
- [ ] Detecta cancelamento via elemento `<event><infEvento><cStat>` = 110111
- [ ] Trata referências (NF referenciada em devolução/complementar)
- [ ] Output normalizado = mesma estrutura que C100/C170 do SPED
- [ ] Logs diferenças se validação XSD falhar (warnings, não erro crítico)

**Dependências:** US-1.3  
**Complexidade:** G  
**Estimativa:** 6–8 dias  

---

### US-1.7: Parser de CT-e XML (Schema v3.0)

**Como** motor de validação,  
**Quero** extrair dados de CT-e XML (chave, transportador, itens, status),  
**Para que** detecte CT-es cancelados indevidamente.

**AC:**
- [ ] Parse XML com validação de schema XSD v3.0
- [ ] Extrai:
  - Chave de acesso CT-e
  - CNPJ transportador, remetente, destinatário
  - Data de emissão
  - Itens de carga: descrição, peso, valor
  - Natura operação (TT = TOTALIZADOR, CTE = transporte)
  - Status: autorizado, cancelado (evento 110111), denegado
  - Protocolo de autorização
- [ ] Detecta cancelamento (mesmo que NF-e)
- [ ] Extrai relacionamento com NF-e via número/série
- [ ] Output normalizado com D100 do SPED

**Dependências:** US-1.6  
**Complexidade:** M  
**Estimativa:** 3–4 dias  

---

### US-1.8: Armazenamento Normalizado em PostgreSQL

**Como** plataforma,  
**Quero** armazenar dados parseados em modelo canônico relacional,  
**Para que** queries analíticas sejam eficientes.

**AC:**
- [ ] Tabelas PostgreSQL:
  - `documents` (id, tenant_id, document_type, upload_id, file_hash, created_at)
  - `fiscal_documents` (id, doc_id, chave_acesso, emitente_cnpj, destinatario_cnpj, data_emissao, natureza, status_nfe, valor_total)
  - `fiscal_items` (id, fiscal_doc_id, item_seq, cfop, ncm, cst, qtd, valor, icms, pis, cofins, ipi)
  - `ct_documents` (id, doc_id, chave_acesso, transportador_cnpj, data_emissao, status_cte, valor)
  - `fiscal_rules_log` (id, doc_id, rule_id, severity, message, created_at)
- [ ] Indexação: `(tenant_id, chave_acesso)`, `(tenant_id, emitente_cnpj, data_emissao)`, `(documento_id, created_at)`
- [ ] RLS habilitado: queries sem `WHERE tenant_id = X` retornam vazio
- [ ] Dados brutos preservados em S3/MinIO como backup (JSON comprimido)
- [ ] Versionamento: campo `document_version` rastreia reprocessamento
- [ ] Audit trail: `created_by`, `created_at`, `updated_at` preenchidos

**Dependências:** US-1.4, US-1.5, US-1.6, US-1.7, EPIC 7, EPIC 8  
**Complexidade:** M  
**Estimativa:** 4–5 dias  

---

### US-1.9: Reprocessamento On-Demand

**Como** analista fiscal,  
**Quero** fazer reprocessamento de arquivo já importado sem gerar duplicatas,  
**Para que** possa corrigir dados após detecção de bug no parser.

**AC:**
- [ ] Endpoint `POST /api/v1/documents/{doc_id}/reprocess`
- [ ] Identifica nova versão via `document_version += 1`
- [ ] Marca versão anterior como `superseded = true`
- [ ] Novos registros criados com `document_version = N`
- [ ] Queries ignoram `superseded` por padrão (exceto audits)
- [ ] Audit trail: log entrada `action=reprocess, reason, triggered_by_user`
- [ ] Não deleta dados anteriores (imutabilidade)
- [ ] Roda em fila assíncrona

**Dependências:** US-1.8  
**Complexidade:** M  
**Estimativa:** 2–3 dias  

---

## 🏗️ Arquitetura Técnica

### Estrutura de Pastas (Backend)

```
backend/
├── app/
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseParser abstrato
│   │   ├── sped_efd_icms.py           # SPED EFD ICMS/IPI
│   │   ├── efd_contribuicoes.py       # EFD Contribuições
│   │   ├── nfe_xml.py                 # NF-e v4.0
│   │   ├── cte_xml.py                 # CT-e v3.0
│   │   └── detector.py                # Auto-detecção de tipo
│   ├── models/
│   │   ├── document.py                # Tabela documents
│   │   ├── fiscal_document.py         # Tabela fiscal_documents
│   │   ├── fiscal_item.py             # Tabela fiscal_items
│   │   ├── ct_document.py             # Tabela ct_documents
│   │   └── upload.py                  # Registro de uploads
│   ├── schemas/
│   │   ├── upload.py                  # UploadRequest, UploadResponse
│   │   ├── document.py                # Schemas Pydantic
│   │   └── parser_output.py           # Schemas de saída dos parsers
│   ├── api/
│   │   ├── uploads.py                 # Rotas POST /uploads
│   │   ├── documents.py               # Rotas GET /documents, PATCH /reprocess
│   │   └── jobs.py                    # Rotas GET /jobs/{job_id}
│   ├── tasks/
│   │   ├── parse_document.py          # Task Celery de parsing
│   │   └── validation.py              # Task Celery de validação pós-parse
│   ├── services/
│   │   ├── upload_service.py          # Orquestração upload
│   │   ├── storage_service.py         # Interface S3/MinIO
│   │   └── parser_service.py          # Factory de parsers
│   └── core/
│       ├── config.py                  # Variáveis de ambiente
│       ├── security.py                # TLS, CORS
│       └── storage.py                 # Inicialização S3/MinIO
├── migrations/
│   └── alembic/
│       └── versions/
│           └── 001_create_document_tables.py
├── tests/
│   ├── unit/
│   │   ├── test_sped_efd_parser.py
│   │   ├── test_nfe_parser.py
│   │   ├── test_detector.py
│   │   └── test_upload_api.py
│   └── integration/
│       └── test_full_upload_flow.py
└── requirements.txt
```

### Stack de Dependências

```txt
# Parsing
lxml==4.9.3              # XML parsing + XSD validation
xmltodict==0.13.0        # XML ↔ dict
pandas==2.1.0            # Dados tabulares (SPED)
pydantic==2.5.0          # Schemas

# API & Web
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
alembic==1.13.0
psycopg==3.1.14          # PostgreSQL driver

# Async
celery==5.3.4
redis==5.0.1

# Storage
boto3==1.29.7            # AWS S3 / MinIO
minio==7.2.2             # MinIO client

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
faker==21.0.0

# Crypto & Validation
python-jose==3.3.0
pydantic-extra-types==2.3.0

# Logging
python-json-logger==2.0.7
```

---

## 🔄 Fluxo de Processamento

```
┌─────────────────┐
│  Cliente: Upload │ (UI ou API)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ 1. Validação de Arquivo     │ (ext, tamanho, checksum)
│    + Detecção de Tipo       │
└────────┬────────────────────┘
         │ ❌ Inválido → Erro 400
         │ ✅ Válido → Enqueue
         ▼
┌─────────────────────────────┐
│ 2. Storage em S3/MinIO      │ (arquivo bruto)
│    + Registro em DB         │ (documents table)
└────────┬────────────────────┘
         │ job_id retornado ao cliente
         ▼
┌─────────────────────────────┐
│ 3. Celery Task:             │
│    - Parser específico      │
│    - Normalização           │
│    - Inserção em tabelas    │
└────────┬────────────────────┘
         │
         ├─ Erro → DLQ + Notificação
         │
         ▼
┌─────────────────────────────┐
│ 4. Trigger EPIC 2           │ (validação de regras)
│    (Chain de tasks Celery)  │
└──────────────────────────────┘
```

---

## 📦 Dependências Entre US

```
US-1.1 (Upload UI)
  └─ US-1.2 (Upload API) ─┐
  └─ US-1.3 (Detector)    ├─ US-1.4 (SPED Parser)
                          ├─ US-1.5 (EFD Parser)
                          ├─ US-1.6 (NF-e Parser)
                          └─ US-1.7 (CT-e Parser)
                                    │
                                    └─ US-1.8 (Storage DB)
                                          │
                                          └─ US-1.9 (Reprocessamento)
```

---

## ✅ Critérios de Aceitação da EPIC

A Epic 1 será considerada **concluída** quando:

1. ✅ Upload de arquivo SPED EFD ICMS/IPI com >1000 linhas processa em <10s
2. ✅ Detecção de tipo acerta >99% dos arquivos
3. ✅ Parser extrai C100/C170/E110 sem perda de dados
4. ✅ XML NF-e parseado identifica cancelamento corretamente
5. ✅ Dados armazenados em PostgreSQL com RLS habilitado
6. ✅ Reprocessamento não gera duplicatas
7. ✅ 3 clientes beta conseguem importar >6 meses de histórico fiscal
8. ✅ Testes unitários cobrem >85% dos parsers
9. ✅ Documentação de API completa (Swagger/OpenAPI)

---

## 📅 Timeline Proposta

| US | Dias | Início | Fim |
|---|---|---|---|
| US-1.3 | 2–3 | D1 | D3 |
| US-1.1 | 3–4 | D1 | D5 |
| US-1.2 | 3–4 | D2 | D6 |
| US-1.4 | 5–7 | D4 | D11 |
| US-1.5 | 4–5 | D7 | D12 |
| US-1.6 | 6–8 | D8 | D16 |
| US-1.7 | 3–4 | D12 | D16 |
| US-1.8 | 4–5 | D11 | D16 |
| US-1.9 | 2–3 | D17 | D19 |

**Total:** ~25–30 dias para equipe de 1–2 desenvolvedores.

---

## 🎯 Próximos Passos

1. **Usar BMAD** para decompor ainda mais em tasks técnicas
2. **Setup inicial:** estrutura de pastas, migrations, dependências Python
3. **Começar por US-1.3 (Detector):** menor escopo, desbloqueia parsers em paralelo
4. **Testes:** test-driven desde o início (fixtures com SPED/XML reais)
