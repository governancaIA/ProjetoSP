# FiscalAI — Arquitetura de Produto: EPICs Completas

---

### EPIC 1: Ingestão e Parsing de Arquivos Fiscais — 🟡 EM ANDAMENTO

**Objetivo de negócio:** Eliminar o processo manual de importação e normalização de arquivos fiscais (SPED EFD ICMS/IPI, EFD Contribuições, XML NF-e, CT-e, NFS-e), que hoje consome horas de analistas e é fonte de erros de truncamento/digitação.

**Valor entregue:** Cliente sobe meses de arquivos fiscais em minutos, com garantia de integridade — reduzindo setup de auditoria de dias para horas.

**Escopo técnico:**
- [x] Upload de arquivos via UI (drag-and-drop) e API REST com suporte a lotes (zip, múltiplos arquivos)
  - AC: arquivos de até 2 GB aceitos; progresso exibido em tempo real; checksum SHA-256 validado no servidor ✅ (`uploads.py` chunked streaming + `storage_service.py` multipart MinIO + `UploadZone.tsx` drag-and-drop com polling de job)
- [x] Parser de SPED EFD ICMS/IPI (blocos 0, C, D, E, G, H, K)
  - AC: registros C100, C170, D100, E110 extraídos sem perda; registros desconhecidos logados como warnings ✅ (`parsers/sped_efd_icms.py` com layout versionado por `0000`; C110 cancelamentos extraídos; chardet para encoding)
- [x] Parser de EFD Contribuições (blocos 0, A, C, D, F, M, P, 1)
  - AC: registros M100, M200, M400, M500 extraídos com PIS/COFINS por CST ✅ (`parsers/efd_contribuicoes.py` + modelos `EFDContribuicoes`/`EFDContribuicoesCst`)
- [x] Parser de XML NF-e (schema v4.0) e CT-e (schema v3.0)
  - AC: parse de chave de acesso, emitente, destinatário, itens, impostos, status de cancelamento e protocolo de autorização ✅ (`parsers/nfe_xml.py` + `parsers/cte_xml.py`)
- [x] Detecção automática de tipo e versão do arquivo
  - AC: classificação correta em >99% dos casos com base em header e estrutura ✅ (`parsers/detector.py`)
- [x] Armazenamento normalizado em PostgreSQL (modelo canônico de documentos fiscais)
  - AC: dados brutos preservados em object storage (S3/MinIO); dados estruturados indexados para queries analíticas ✅ (`models/fiscal_document.py` + `services/storage_service.py` + MinIO multipart)
- [ ] Reprocessamento on-demand de arquivos já importados
  - AC: novo parse não duplica dados; versão anterior marcada como superseded com audit trail ❌ (pendente — planejado em EPIC 18)

**Stack envolvida:** Python (lxml, xmltodict, pandas para EFD), FastAPI, Celery, PostgreSQL, MinIO/S3, Redis

**Dependências:** EPIC 8 (pipeline assíncrono), EPIC 7 (multi-tenancy)

**Estimativa:** G

**Prioridade:** MVP

---

### EPIC 2: Motor de Validação e Regras Fiscais — 🟡 EM ANDAMENTO (8/9 regras MVP implementadas)

**Objetivo de negócio:** Codificar o conhecimento tributário brasileiro como regras executáveis — substituindo o analista fiscal que valida manualmente centenas de campos contra IN RFB, COTEPE, CONFAZ e ADE Cotec.

**Valor entregue:** Validação consistente, auditável e sempre atualizada — sem depender de expertise individual de cada cliente.

**Escopo técnico:**
- [x] Engine de regras baseada em DAG de validações com versionamento semântico
  - AC: regras habilitadas/desabilitadas por tenant; resultado de cada regra logado individualmente com versão ✅ (`validators/rules/dag.py` + `registry.py` + `RuleService` com `TenantConfig` overrides)
- [x] Regra: NF-e escriturada vs XML — divergência de valor total, base de cálculo, alíquota
  - AC: diferença >R$0,01 gera alerta; tolerância configurável por tenant ✅ (`NfeValorDivergente` — tolerância via `TenantConfig`)
- [x] Regra: notas canceladas (evento 110111) ainda presentes no SPED
  - AC: cruzamento de evento de cancelamento com C100/C170; qualquer nota cancelada escriturada gera alerta CRÍTICO ✅ (`NfeCanceladaNoSped` — detecta via C110 extraído pelo parser)
- [x] Regra: nota de saída sem lançamento correspondente no livro fiscal
  - AC: toda NF-e autorizada de saída deve ter registro C100 correspondente no EFD do período ✅ (parcial — heurística interna ao documento; cruzamento SPED×XML de XMLs externos pendente)
- [x] Regra: CT-e cancelado escriturado indevidamente
  - AC: cruzamento D100 com eventos de cancelamento CT-e ✅ (`CteCanceladoNoSped`)
- [x] Regra: divergência de ICMS entre calculado e declarado
  - AC: tolerância de R$0,50 por item; considera diferimento, ST e isenções por CFOP/CST ✅ (`IcmsDivergente`)
- [x] Regra: PIS/COFINS — CST incompatível com regime tributário do emitente
  - AC: Lucro Presumido não pode usar CST 01/02/03; Simples Nacional não escritura PIS/COFINS ✅ (`CstIncompativelPisCofins` — tabela `cst_icms_reference` no BD)
- [ ] Regra: IPI — alíquota divergente da TIPI para o NCM declarado
  - AC: integração com tabela TIPI vigente; atualização mensal automática ❌ (tabela TIPI >10k NCMs pendente — EPIC 12)
- [x] Regra: CFOP inválido para operação (UF origem vs destino, natureza)
  - AC: validação de CFOP inter/intraestadual; CFOP de devolução exige NF referenciada ✅ (`CfopInvalido` — tabela `cfop_reference` no BD)

**Stack envolvida:** Python (pydantic para schemas de regras), PostgreSQL (tabelas TIPI, CFOP, CST), Redis (cache de referências), Celery

**Dependências:** EPIC 1 (dados normalizados), EPIC 4 (scoring consome output das regras)

**Estimativa:** G

**Prioridade:** MVP

---

### EPIC 3: Detecção de Inconsistências com IA e Heurísticas — 🔲 NÃO INICIADA

**Objetivo de negócio:** Ir além das regras determinísticas — identificar padrões anômalos que regras fixas não capturam: fornecedores suspeitos, sazonalidade irregular, sequências de notas incomuns.

**Valor entregue:** Detecta inconsistências que escapariam de auditoria manual convencional — aumentando cobertura de risco sem aumentar custo.

**Escopo técnico:**
- [ ] Anomaly detection em valores de NF por fornecedor (Isolation Forest / Z-score)
  - AC: notas com valor >3σ da média histórica do fornecedor geram alerta; modelo retreinado mensalmente por tenant
- [ ] Detecção de sequências suspeitas (gaps, duplicatas, retroatividade)
  - AC: gap >10 números em NFs próprias gera alerta; NF com data retroativa >5 dias gera alerta
- [ ] Detecção de notas "fantasmas" — CNPJ emitente inapto na data de emissão
  - AC: validação de situação cadastral via Receita Federal; CNPJ inapto/cancelado na data da NF gera alerta CRÍTICO
- [ ] Heurística de "nota de passagem" — triangulações suspeitas
  - AC: mesmo item em >2 CNPJs do mesmo grupo econômico em <48h
- [ ] Clustering de fornecedores por comportamento fiscal (benchmark de setor)
  - AC: fornecedores agrupados por setor/porte; outliers dentro do cluster identificados
- [ ] Score de confiabilidade por fornecedor
  - AC: fornecedores rankeados por taxa histórica de inconsistências; score exibido no dashboard

**Stack envolvida:** Python (scikit-learn, pandas, numpy), PostgreSQL, Celery (ML batch), MLflow (Fase 2)

**Dependências:** EPIC 1, EPIC 2 (dados validados alimentam modelos), EPIC 4

**Estimativa:** G

**Prioridade:** Fase 2 (heurísticas simples no MVP; ML supervisionado na Fase 2)

---

### EPIC 4: Scoring de Risco Fiscal e Classificação de Severidade — 🟡 EM ANDAMENTO (MVP core concluído)

**Objetivo de negócio:** Transformar centenas de alertas brutos em visão priorizada de risco — para que o analista saiba exatamente onde agir primeiro, sem vasculhar planilhas.

**Valor entregue:** Reduz tempo de triagem de horas para minutos; priorização por impacto financeiro real.

**Escopo técnico:**
- [x] Modelo de scoring por alerta (CRÍTICO / ALTO / MÉDIO / BAIXO / INFORMATIVO)
  - AC: CRÍTICO = potencial multa >R$10k ou irregularidade dolosa; BAIXO = divergência <R$100; critérios configuráveis por tenant ✅ (`services/scoring_service.py` — `calculate_alert_severity()` + estimativa de exposição via DL 1598)
- [x] Score de risco agregado por período (competência mensal), escala 0–100
  - AC: histórico de evolução exibido em gráfico de tendência; delta entre períodos com causa raiz ✅ (`get_period_score()` — joinedload elimina N+1; endpoints `GET /periods/{year}/{month}/score`)
- [ ] Score consolidado para grupos econômicos com múltiplos CNPJs
  - AC: visão agregada quando tenant tem múltiplos CNPJs cadastrados ❌ (pendente — requer modelagem multi-CNPJ)
- [x] Estimativa de exposição financeira por inconsistência (tabela de penalidades)
  - AC: cálculo baseado em art. 12 DL 1598 e Portaria CAT; exibido em R$ ✅
- [x] Priorização automática de fila de trabalho
  - AC: fila ordenada por (severidade × exposição financeira × probabilidade de autuação) ✅ (`get_alert_prioritization_queue()` — endpoint `GET /alerts/priority-queue`)

**Stack envolvida:** Python (lógica de scoring), PostgreSQL, FastAPI

**Dependências:** EPIC 2 (alertas de regras), EPIC 3 (alertas de IA)

**Estimativa:** M

**Prioridade:** MVP

---

### EPIC 5: Dashboard Executivo e Visualização de Alertas — 🟡 EM ANDAMENTO (Dashboard MVP concluído)

**Objetivo de negócio:** Dar ao CFO, controller e analista fiscal uma visão unificada e interativa — tornando a plataforma o centro de comando da saúde fiscal da empresa.

**Valor entregue:** Visibilidade imediata do risco sem precisar de analista intermediário para interpretar dados brutos.

**Escopo técnico:**
- [x] Dashboard home: score atual, evolução 12 meses, top-5 inconsistências críticas
  - AC: carregamento <2s; dados atualizados após cada processamento de arquivo ✅ (`pages/DashboardPage.tsx` — KPI cards, AlertsTable, SeverityChart pizza, TopFailedRules, PeriodSelector)
- [x] Tela de alertas com filtros avançados (severidade, tipo, período, CNPJ, valor)
  - AC: filtros combinados; paginação de até 10k alertas sem degradação; exportação da lista filtrada ✅ (`pages/AlertsPage.tsx` — filtros CRITICAL/HIGH/MEDIUM/LOW/INFORMATIVE, tabela paginada com expand de detalhes)
- [x] Drilldown de documento: score de risco, resultados de validação por regra
  - AC: `DocumentDetailPage.tsx` com `ScoreGauge`, exposição financeira, `ValidationTable` com 7 regras ✅ (diff visual XML lado-a-lado ainda pendente)
- [ ] Diff visual XML original vs dado escriturado (lado a lado)
  - AC: diferença destacada em vermelho; clique abre XML completo ❌ (pendente — requer armazenamento de XML bruto por chave_acesso)
- [ ] Visão por fornecedor: histórico de inconsistências e score de confiabilidade
  - AC: ranking de fornecedores por número/valor de inconsistências; gráfico de tendência ❌
- [ ] Heatmap de risco fiscal por competência (calendário 12 meses)
  - AC: cor proporcional ao score; click abre detalhes do período ❌
- [ ] Notificações in-app e email para alertas CRÍTICOS
  - AC: disparo em <5min após detecção; configurável por usuário ❌

**Stack envolvida:** React + TypeScript, Recharts/Victory (gráficos), FastAPI (BFF), PostgreSQL

**Dependências:** EPIC 4 (scores e alertas), EPIC 7 (auth e multi-tenancy)

**Estimativa:** G

**Prioridade:** MVP

---

### EPIC 6: Relatórios e Exportação (PDF, Excel, Auditoria Rastreável) — 🟡 EM ANDAMENTO (PDF + Excel MVP concluídos)

**Objetivo de negócio:** Viabilizar que os resultados da plataforma sejam usados em defesas fiscais, reuniões com auditores da Receita e apresentações para board — onde credibilidade do dado é tão importante quanto o dado.

**Valor entregue:** Relatório auditável substitui horas de formatação manual; evidência estruturada reduz custo de defesa em auto de infração.

**Escopo técnico:**
- [x] Relatório executivo PDF: sumário de risco, top inconsistências, score, narrativa IA
  - AC: gerado em <30s ✅ (`services/report_service.py` ReportLab — KPIs, narrativa IA via Claude Haiku com prompt caching, top regras, alertas; white-label via `BRAND_*` settings; endpoint `GET /reports/period/{year}/{month}/pdf`)
- [x] Relatório detalhado por tipo de inconsistência (Excel)
  - AC: aba Resumo + aba Alertas com colunas severidade/regra/emitente/chave/valor/exposição/mensagem ✅ (`generate_excel_report()` openpyxl; endpoint `GET /reports/period/{year}/{month}/excel`)
- [ ] Exportação de trilha de auditoria completa (imutável, com IP e timestamp UTC)
  - AC: log de todas as ações do usuário exportável em CSV ❌
- [ ] Relatório comparativo entre períodos (mês a mês, ano a ano)
  - AC: delta de inconsistências entre dois períodos; evolução de exposição financeira ❌
- [ ] Agendamento de relatórios periódicos (mensal automático D+5)
  - AC: relatório gerado automaticamente no D+5 após fechamento da competência; enviado por email em PDF ❌

**Stack envolvida:** Python (WeasyPrint/ReportLab para PDF, openpyxl para Excel), Celery, S3/MinIO

**Dependências:** EPIC 4, EPIC 5 (mesmos dados, formato diferente)

**Estimativa:** M

**Prioridade:** MVP (PDF básico + CSV); Fase 2 (agendamento + comparativos)

---

### EPIC 7: Multi-tenancy, Autenticação e Controle de Acesso — 🟡 EM ANDAMENTO (MVP auth + multi-tenancy concluídos)

**Objetivo de negócio:** Suportar múltiplos clientes com isolamento total de dados e controle granular de permissões — requisito obrigatório para SaaS B2B com dados fiscais sensíveis.

**Valor entregue:** Segurança e compliance nativos — isolamento técnico auditável sem depender de "confiar na palavra" da plataforma.

**Escopo técnico:**
- [x] Multi-tenant com schema isolation no PostgreSQL (RLS habilitado, schema por tenant)
  - AC: query sem WHERE de tenant_id retorna vazio; schemas completamente isolados entre tenants ✅ (`core/database.py` sanitização tenant_id + `core/middleware.py` TenantMiddleware; schema criado atomicamente no register; migration 001)
- [x] Autenticação JWT + refresh token com rotação
  - AC: access token TTL 30min; refresh token TTL 7 dias; revogação imediata por logout ✅ (`services/auth_service.py` + `api/auth.py`; blacklist Redis pós-logout)
- [ ] SSO/SAML 2.0 para enterprise (Azure AD, Okta)
  - AC: login via IdP externo; provisionamento automático no primeiro login ❌
- [x] RBAC: Admin + Analista Fiscal (MVP)
  - AC: roles implementados; Admin acessa todas as rotas; permissões por role no JWT ✅ (parcial — 2 de 4 roles; Controller e Auditor Externo pendentes)
- [x] Suporte a múltiplos CNPJs via TenantConfig
  - AC: `TenantConfig` com CNPJ principal, regime tributário, UF, tolerâncias ✅ (parcial — visão consolidada multi-CNPJ pendente)
- [x] Wizard de onboarding de tenant (regime tributário, CNPJ, validação)
  - AC: configuração em <10min; CNPJ validado via algoritmo dígito verificador ✅ (`core/validators.py` + `POST /auth/onboarding` + `GET /auth/onboarding/status`)

**Stack envolvida:** FastAPI + python-jose (JWT), PostgreSQL (RLS + schemas), python-saml / authlib (SSO)

**Dependências:** Fundação para todas as outras EPICs

**Estimativa:** G

**Prioridade:** MVP

---

### EPIC 8: Pipeline Assíncrono e Processamento Escalável — 🟡 EM ANDAMENTO (Celery básico funcional)

**Objetivo de negócio:** Garantir que processamento de arquivos grandes (SPED de 500k NFs/mês) não trave a plataforma nem degrade a experiência de outros tenants.

**Valor entregue:** SLA de processamento previsível; plataforma não degrada sob carga; custo de infra escala proporcionalmente ao uso.

**Escopo técnico:**
- [x] Filas com Celery + Redis (fila única MVP)
  - AC: jobs de parse assíncrono funcionais; `job_id` retornado no upload; status consultável via `GET /jobs/{job_id}` ✅ (`tasks/parse_document.py` + `tasks/validate_document.py` + `api/jobs.py`; filas separadas por tipo pendente — EPIC 17)
- [ ] Workers auto-scaling baseado em profundidade de fila (K8s HPA)
  - AC: profundidade >100 jobs dispara scale-out; idle >5min dispara scale-in; tempo de scale <2min ❌
- [ ] Chunking de arquivos grandes em chunks paralelos
  - AC: resultado consolidado sem duplicatas ❌ (streaming sequencial existe; paralelismo pendente)
- [x] Retry com backoff exponencial (máx. 3 tentativas: 1min/5min/15min)
  - AC: falha definitiva notifica o usuário ✅ (`autoretry_for` + `max_retries=3` nas tasks Celery)
- [ ] Dead letter queue (DLQ) com reprocessamento manual via painel admin
  - AC: jobs em DLQ visíveis; reprocessamento com 1 clique ❌
- [ ] Rate limiting por tenant para uploads
  - AC: plano básico 10 uploads/dia, 100MB/arquivo; enterprise ilimitado com throttling ❌

**Stack envolvida:** Celery, Redis, Docker, Kubernetes (HPA), Flower

**Dependências:** Base para EPICs 1, 2, 3

**Estimativa:** M

**Prioridade:** MVP

---

### EPIC 9: API Pública e Integrações com ERPs — 🔲 NÃO INICIADA

**Objetivo de negócio:** Permitir que o FiscalAI seja consumido por sistemas do cliente (ERP, BI) e parceiros integradores — expandindo o mercado além de usuários que fazem upload manual.

**Valor entregue:** Integração com ERP elimina upload manual; abre canal de revenda via integradores; habilita dados em tempo real.

**Escopo técnico:**
- [ ] API REST pública versionada (v1) com documentação OpenAPI/Swagger completa
  - AC: toda rota documentada com exemplos; changelog público de breaking changes
- [ ] Autenticação via API Keys com escopos (read-only, write, admin)
  - AC: API Key gerada por tenant; revogação imediata; log de cada chamada
- [ ] Webhooks para eventos (novo alerta crítico, processamento concluído)
  - AC: retry automático por 24h em caso de falha; payload assinado com HMAC
- [ ] Endpoint de ingestão de NF-e via API (XML individual ou lote de até 100)
  - AC: processamento assíncrono; status consultável via job_id
- [ ] Conector nativo para SAP B1 e TOTVS Protheus
  - AC: sincroniza NFs automaticamente a cada fechamento de período
- [ ] SDK Python e Node.js (disponíveis em PyPI e npm)
  - AC: exemplos de uso para os 5 endpoints mais comuns

**Stack envolvida:** FastAPI (API pública), PostgreSQL (API keys, webhooks), Redis (rate limiting)

**Dependências:** EPIC 7 (auth), EPIC 1 (mesma lógica de ingestão)

**Estimativa:** M (API base) / G (conectores ERP)

**Prioridade:** Fase 2

---

### EPIC 10: Segurança, LGPD e Observabilidade — 🟡 EM ANDAMENTO (fundação concluída via EPICs 13+18)

**Objetivo de negócio:** Dados fiscais são extremamente sensíveis (CNPJ, faturamento, fornecedores estratégicos). Vazamento gera responsabilidade legal e destruição de reputação. LGPD exige controles documentáveis.

**Valor entregue:** Cliente enterprise aprova vendor security review; plataforma auditável por DPO; incidentes detectados antes de virar crise.

**Escopo técnico:**
- [ ] Criptografia em repouso: AES-256, chave por tenant, rotação sem downtime
  - AC: backup criptografado; chave nunca exposta em logs
- [ ] TLS 1.3 obrigatório, HSTS habilitado, certificados gerenciados
  - AC: sem suporte a TLS <1.2; HTTP redireciona para HTTPS
- [ ] Audit log imutável e append-only de todas as ações
  - AC: cada ação com user_id, tenant_id, action, resource, timestamp, IP; não deletável pelo tenant
- [ ] LGPD: relatório de dados por titular, direito de exclusão e portabilidade
  - AC: relatório em <1min; exclusão remove PII em <24h mantendo logs anonimizados
- [ ] Detecção de comportamento anômalo (login de país incomum, bulk export)
  - AC: novo país bloqueia sessão até MFA; export >1000 registros gera alerta para admin
- [ ] Observabilidade: Prometheus (métricas), JSON logs estruturados (ELK), OpenTelemetry (traces)
  - AC: p95 de latência disponível em Grafana; erro 5xx gera alerta em <2min
- [ ] Política de retenção de dados configurável por tenant (1/3/5/7 anos)
  - AC: dados além da retenção deletados automaticamente com audit trail

**Stack envolvida:** Python (cryptography), PostgreSQL (RLS, TDE), OpenTelemetry, Prometheus, Grafana, ELK

**Dependências:** EPIC 7 (identidade base), EPIC 8 (logs de jobs)

**Estimativa:** G

**Prioridade:** MVP (TLS + auth segura + audit log básico); Fase 2 (LGPD completa + observabilidade)

---

### EPIC 11: Onboarding, Planos e Monetização SaaS — 🔲 NÃO INICIADA

**Objetivo de negócio:** Converter trials em clientes pagantes e maximizar LTV — com pricing baseado em valor (volume de NFs, número de CNPJs) e onboarding que entrega o primeiro "aha moment" em <24h.

**Valor entregue:** Receita recorrente previsível; time-to-value mínimo; expansão natural com crescimento do cliente.

**Escopo técnico:**
- [ ] Trial auto-serve de 14 dias (sem cartão), limitado a 1 CNPJ e 3 meses de dados
  - AC: cadastro em <2min via email; first file processed em <10min
- [ ] Planos: Starter (1 CNPJ, 10k NFs/mês) / Pro (5 CNPJs, 100k NFs/mês) / Enterprise (ilimitado + SLA)
  - AC: upgrade sem perda de dados; downgrade bloqueia features mas mantém dados por 90 dias
- [ ] Cobrança via Stripe (cartão, boleto, PIX para enterprise)
  - AC: invoice automática mensal/anual; 3 tentativas de cobrança em 7 dias com email; dados preservados 30 dias após cancelamento
- [ ] Portal de faturamento self-service (faturas, troca de cartão, upgrade/downgrade)
  - AC: 100% das questões de faturamento resolvíveis sem contato com suporte
- [ ] Métricas de produto (usage tracking por feature, cohort analysis)
  - AC: eventos enviados para data warehouse; dashboard de product analytics para time interno
- [ ] Programa de referência para integradores contábeis
  - AC: link rastreável; comissão de 20% no primeiro ano; dashboard de comissões para o parceiro

**Stack envolvida:** Stripe API (stripe-python), PostgreSQL (planos, metering), PostHog/Mixpanel

**Dependências:** EPIC 7 (tenants), EPIC 8 (metering de uso)

**Estimativa:** M

**Prioridade:** Fase 2

---

### EPIC 12: Atualização Automática de Legislação Fiscal — 🔲 NÃO INICIADA

**Objetivo de negócio:** A legislação fiscal brasileira muda constantemente (novas versões SPED, mudanças de alíquota, novos CFOPs, atualizações TIPI). Manter regras atualizadas manualmente é inviável e fonte de falsos negativos críticos.

**Valor entregue:** Motor de regras sempre atualizado sem intervenção manual — cliente não precisa monitorar o Diário Oficial.

**Escopo técnico:**
- [ ] Pipeline de atualização da tabela TIPI (IPI por NCM) — fonte: Receita Federal
  - AC: verificação semanal; mudanças aplicadas automaticamente; versão anterior mantida para reprocessamento de períodos passados
- [ ] Pipeline de atualização de CFOPs válidos (ADE COTEPE)
  - AC: novos CFOPs detectados e incorporados em <7 dias após publicação
- [ ] Pipeline de novas versões de schema SPED (EFD, ECD, ECF)
  - AC: novo schema detectado via Portal SPED; parsers atualizados via feature flag antes da obrigatoriedade
- [ ] Changelog público de atualizações de regras para tenants
  - AC: toda mudança publicada em feed in-app; tenant notificado quando regra retroativa afeta seus dados
- [ ] Backtesting automático de nova versão de regra contra dados históricos
  - AC: nova regra roda em shadow mode por 7 dias; delta de alertas reportado para equipe fiscal interna antes de ir para produção

**Stack envolvida:** Python (scrapy/playwright para scraping), Celery (jobs periódicos), PostgreSQL (versionamento de tabelas de referência), LaunchDarkly/Unleash (feature flags)

**Dependências:** EPIC 2 (consome tabelas de referência), EPIC 8 (jobs periódicos)

**Estimativa:** M

**Prioridade:** Fase 2

---

## ROADMAP RESUMIDO

### MVP — 30 dias
*Objetivo: plataforma funcional para 5–10 clientes beta, 1 segmento (ex: Lucro Real, ICMS/IPI)*

| Epic | Escopo no MVP |
|------|--------------|
| EPIC 7 | Multi-tenancy básico, JWT auth, RBAC Admin + Analista |
| EPIC 8 | Celery + Redis funcional, filas básicas, retry simples |
| EPIC 1 | Parser NF-e XML + SPED EFD ICMS/IPI (C100, C170, E110) |
| EPIC 2 | 5 regras core: NF cancelada no SPED, divergência NF×XML, saída sem lançamento, CFOP básico |
| EPIC 4 | Scoring básico por severidade + estimativa de exposição financeira |
| EPIC 5 | Dashboard simples: score, lista de alertas com filtros |
| EPIC 6 | Exportação CSV + PDF executivo básico |
| EPIC 10 | TLS, auth segura, audit log básico |

**Critério de saída:** 3 empresas beta usando semanalmente; >10 inconsistências reais detectadas e confirmadas por analistas fiscais.

---

### Beta — 90 dias
*Objetivo: cobertura completa SPED + EFD Contribuições + CT-e; pricing funcionando; 50 clientes ativos*

| Epic | Escopo Beta |
|------|-------------|
| EPIC 1 | Parser EFD Contribuições (M100, M200) + CT-e + NFS-e |
| EPIC 2 | 15+ regras: PIS/COFINS por CST, IPI×TIPI, EFD Contribuições completa |
| EPIC 3 | Heurísticas: CNPJ inapto, gaps de numeração, Z-score de valores por fornecedor |
| EPIC 4 | Score por período, evolução histórica, fila priorizada |
| EPIC 5 | Dashboard completo: heatmap, drilldown, visão por fornecedor |
| EPIC 6 | Relatório comparativo de períodos, agendamento mensal automático |
| EPIC 10 | LGPD básico, Prometheus + Grafana, alertas de incidente |
| EPIC 11 | Trial 14 dias + 3 planos + Stripe (cartão + boleto) |
| EPIC 12 | Pipeline TIPI e CFOP automático |

**Critério de saída:** MRR > R$50k; NPS > 40; churn <5%/mês.

---

### Escala — 180 dias
*Objetivo: plataforma enterprise, integrações ERP, ML completo, ecossistema de parceiros integradores*

| Epic | Escopo Escala |
|------|---------------|
| EPIC 3 | ML supervisionado completo (Isolation Forest por tenant), clustering de fornecedores |
| EPIC 9 | API pública v1, webhooks, SDK Python/Node, conector TOTVS Protheus |
| EPIC 10 | SSO/SAML enterprise, gestão avançada de incidentes, SLA 99.9% |
| EPIC 11 | Plano Enterprise + SLA + suporte dedicado; programa de integradores com dashboard de comissões |
| EPIC 12 | Backtesting automático de regras, schema SPED automático |
| EPIC 2 | Expansão para ECD, ECF e contribuições previdenciárias (e-Social fiscal) |

**Critério de saída:** MRR > R$300k; 3 integradores ativos no programa de parceiros; primeiro cliente enterprise >R$5k/mês contratado.

---

**Ordem lógica de dependências:**
`EPIC 7 → EPIC 8 → EPIC 1 → EPIC 2 → EPIC 4 → EPIC 5 → EPIC 6 → EPIC 3 → EPIC 10 → EPIC 12 → EPIC 9 → EPIC 11`

---

---

## EPICS DE MELHORIA ARQUITETURAL

> Geradas a partir da revisão arquitetural de 2026-05-25.
> Devem ser executadas em paralelo às epics de produto, priorizadas por severidade.
> Pré-requisito: correções críticas (EPIC 13) devem ser concluídas antes de qualquer deploy para clientes reais.

---

### EPIC 13: Correções de Segurança e LGPD Críticas ✅ CONCLUÍDA (2026-05-26)

**Objetivo:** Eliminar vulnerabilidades que podem causar violação de dados fiscal (LGPD Art. 46) ou comprometimento total da autenticação antes do primeiro cliente real.

**Escopo técnico:**
- [x] Sanitizar `tenant_id` antes de interpolação em `SET search_path` — `core/database.py`
  - AC: regex `^[a-zA-Z0-9_-]{3,100}$` aplicada; qualquer valor fora do padrão levanta `ValueError` com log de segurança ✅
- [x] Validar `SECRET_KEY` no startup da aplicação — `main.py` lifespan
  - AC: se `SECRET_KEY` for o valor default e `DEBUG=False`, aplicação não sobe; warning em modo dev ✅
- [x] Criar função `mask_chave_acesso()` e aplicar em todos os logs e `RuleExecutionLog.message`
  - AC: CNPJ (posições 6–19 da chave de 44 dígitos) mascarado como `***`; aplicado em 3 regras fiscais ✅
- [x] Restringir `CORS_ORIGINS` — nunca `"*"` com `allow_credentials=True` em produção
  - AC: `model_validator` em `core/config.py` rejeita combinação insegura em produção ✅
- [x] Rate limiting em `/api/v1/auth/login` com `slowapi`
  - AC: máx. 5 tentativas por IP por minuto; resposta 429 com `Retry-After` ✅
- [x] Rate limiting em `/api/v1/auth/register` — adicionado na revisão pós-review
  - AC: máx. 3 tentativas por IP por minuto ✅
- [x] Email não vaza em mensagem de erro de registro — LGPD
  - AC: mensagem genérica "Email já cadastrado" sem expor o endereço ✅

**Commits:** `3d0cf25` (AC1,2,4,5), `2dfd243` (AC3 mask_chave_acesso), `fix-review` (AC rate limit /register + email LGPD)

---

### EPIC 14: Fundação Multi-Tenancy Completa ✅ CONCLUÍDA (2026-05-26)

**Objetivo:** Completar o que está parcialmente implementado no Epic 7 — sem isso, novos tenants não têm schema e dados podem vazar entre tenants em produção.

**Escopo técnico:**
- [x] Endpoint de signup cria schema PostgreSQL atomicamente junto com o usuário
  - AC: `POST /api/v1/auth/register` chama `create_tenant_schema(tenant_id)` com compensating transaction ✅
- [x] Middleware FastAPI que seta `search_path` em cada request autenticado
  - AC: `TenantMiddleware` extrai `tenant_id` do JWT sem DB lookup; `get_db()` em `api/deps.py` executa `SET search_path` na sessão entregue aos handlers; todos os routers usam `get_db` de `deps.py` ✅
- [x] Substituir `NullPool` por `QueuePool` com limites explícitos
  - AC: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True` ✅
- [x] Modelo `TenantConfig` no schema `public` com regime tributário, CNPJ principal, UF, tolerâncias
  - AC: migration `002_tenant_config.py`; `RuleService.get_config()` consome `TenantConfig` ✅
- [x] Wizard de onboarding: validar CNPJ + salvar `TenantConfig`
  - AC: `validate_cnpj()` em `core/validators.py` (algoritmo oficial de dígitos verificadores); `POST /auth/onboarding` idempotente; `GET /auth/onboarding/status` ✅

**Commits:** `5bcaada` (implementação principal), fixes de review (middleware bug, onboarding_completed Boolean)

**Arquivos afetados:** `core/database.py`, `core/middleware.py` (novo), `core/validators.py` (novo), `api/auth.py`, `api/deps.py`, `models/tenant_config.py`, `services/auth_service.py`, `schemas/auth.py`

**Estimativa:** M (1 semana)

**Prioridade:** Alto — executa logo após EPIC 13

---

### EPIC 15: Completude do Parser SPED e Cruzamento SPED × XML ✅ CONCLUÍDA (2026-05-26)

**Objetivo:** Corrigir gaps no parser que fazem regras fiscais críticas nunca dispararem — especialmente cancelamentos e divergências entre SPED e XML da SEFAZ.

**Escopo técnico:**
- [x] Extração de eventos de cancelamento do registro C110 (bloco C) e atualização de `status_nfe`
  - AC: `cod_inf = "110111"` detectado; `c100["status_nfe"]` atualizado para `"cancelado"` no pós-processamento; regra `nfe_cancelada_no_sped` passa a disparar ✅
- [x] Detecção de encoding automática antes do decode (`chardet`) — `parsers/sped_efd_icms.py`
  - AC: `parse_bytes()` detecta Latin-1/UTF-8 via chardet com fallback; arquivos pré-2015 parseados sem perda ✅
- [x] Validação do layout C100 contra versão do arquivo (registro `0000`)
  - AC: versão extraída do `0000`; `_get_layout()` seleciona mapeamento por versão (014/015/016/017+); warning se versão desconhecida ✅
- [x] Parser de EFD Contribuições: registros M100, M200, M400, M500
  - AC: `EFDContribuicoesParser` + modelos `EFDContribuicoes`/`EFDContribuicoesCst` + migration 005; PIS/COFINS por CST extraídos ✅
- [ ] Implementação real da regra `saida_sem_lancamento` via cruzamento SPED × XML por `chave_acesso`
  - **Pendente:** requer integração com serviço de storage de XMLs NF-e (a ser feito em EPIC 17+)

**Arquivos afetados:** `parsers/sped_efd_icms.py`, `parsers/efd_contribuicoes.py` (novo), `models/efd_contribuicoes.py` (novo), `migrations/versions/005_efd_contribuicoes.py` (novo), `parsers/__init__.py`, `models/__init__.py`

**Commits:** implementação EPIC 15+16 (2026-05-26)

---

### EPIC 16: Tabelas de Referência Fiscal no Banco ✅ CONCLUÍDA PARCIAL (2026-05-26)

**Objetivo:** Mover dados de referência fiscal (CFOPs, CSTs, TIPI/NCM) de listas hardcoded no Python para tabelas versionadas no PostgreSQL schema `public` — permitindo atualização sem deploy.

**Escopo técnico:**
- [x] Tabela `cfop_reference` com todos os CFOPs válidos, descrição, tipo (entrada/saída), indicador inter/intraestadual
  - AC: migration 003 com dados completos ADE COTEPE; `RuleService.get_config` carrega e popula `valid_cfops` + `cfop_metadata`; `cfop_invalido` usa nível 2 quando disponível ✅
- [x] Tabela `cst_icms_reference` com CSTs válidos por regime tributário
  - AC: migration 004; colunas `regime_lucro_real`, `regime_lucro_presumido`, `regime_simples`; `RuleService.get_config` popula `valid_csts_all` + `valid_csts_regime`; `cst_incompativel` usa banco como prioridade ✅
- [ ] Tabela `tipi_ncm` com alíquotas IPI por NCM (fonte: Receita Federal)
  - **Pendente:** complexidade da tabela TIPI (>10k NCMs) — postergado para fase pós-MVP
- [x] Tabela `ibge_uf` com códigos de UF para validação de chave de acesso
  - AC: migration 004; 27 UFs + DF incluídos ✅
- [ ] Endpoint admin `POST /api/v1/admin/reference-data/reload` para recarregar tabelas sem deploy
  - **Pendente:** postergado para EPIC 18 (observabilidade/admin)

**Arquivos afetados:** `models/cst_icms_reference.py` (novo), `models/ibge_uf.py` (novo), `migrations/versions/004_cst_ibge_reference.py` (novo), `services/rule_service.py`, `validators/rules/fiscal_rules.py`, `models/__init__.py`

**Commits:** implementação EPIC 15+16 (2026-05-26)

---

### EPIC 17: Performance e Escalabilidade do Pipeline — 🟡 EM ANDAMENTO (streaming + N+1 concluídos)

**Objetivo:** Eliminar gargalos que causam crash ou timeouts em produção com volume real de dados fiscais.

**Escopo técnico:**
- [x] Streaming upload para MinIO com hash SHA-256 calculado em chunks — `api/uploads.py`, `services/storage_service.py`
  - AC: arquivos de até 2GB processados sem carregar em RAM; hash calculado durante o stream; multipart upload para MinIO ✅ (`_iter_upload` 8MB chunks + `StorageService` multipart threshold 100MB, parts 50MB; SHA-256 calculado no stream)
- [x] Refatorar `get_period_score` para eliminar N+1 — `services/scoring_service.py`
  - AC: `joinedload(FiscalDocument.rule_logs)` substitui N queries separadas; p95 melhorado ✅ (parcial — joinedload ao invés de SQL GROUP BY puro; otimização adicional com query agregada pendente para >10k docs)
- [ ] Paginação real via SQL em `get_alert_prioritization_queue`
  - AC: `OFFSET/LIMIT` na query; nunca carrega todos os logs em memória; cursor-based pagination para >10k registros ❌
- [ ] Filas Celery separadas por tipo de trabalho
  - AC: `queue_parse` (I/O intensivo, 4 workers), `queue_validate` (CPU, 2 workers), `queue_scoring` (lazy); upload massivo de um tenant não bloqueia outros ❌ (sem `task_routes` no `celery_app.py`)
- [ ] Cache Redis para scores de períodos fechados
  - AC: TTL de 15 minutos; invalidado automaticamente após novo processamento de arquivo do período; hit rate > 80% em produção ❌

**Arquivos afetados:** `api/uploads.py`, `services/storage_service.py`, `services/scoring_service.py`, `core/celery_app.py`, `tasks/validate_document.py`

**Estimativa:** M (1 semana)

**Prioridade:** Alto — streaming upload é bloqueador de produção; N+1 causa timeout em escala

---

### EPIC 18: Observabilidade e Health Check Real — 🟡 EM ANDAMENTO (health check + logs concluídos)

**Objetivo:** Dar visibilidade real ao estado da aplicação — sem isso, o load balancer pensa que tudo está saudável mesmo com banco fora, e incidentes ficam invisíveis.

**Escopo técnico:**
- [x] Health check com verificação real de dependências — `main.py`
  - AC: `GET /health` verifica PostgreSQL (`SELECT 1`), Redis (PING), MinIO (list_buckets); retorna `"healthy"` ou `"degraded"` com detalhe por componente ✅
- [ ] Endpoint de reprocessamento retroativo por tenant — `api/` (novo endpoint admin)
  - AC: `POST /api/v1/admin/tenants/{tenant_id}/revalidate` aceita `from_date` e `rule_ids`; dispara revalidação em background via Celery; status consultável via `job_id` ❌
- [x] Logs estruturados JSON com campos padronizados (sem PII)
  - AC: todos os logs em formato JSON com `tenant_id` (mascarado), `document_id`, `rule_id`; sem `chave_acesso` ou CNPJ em texto plano ✅ (`core/logging_config.py` JSON logging; `mask_chave_acesso()` em regras fiscais)
- [ ] Métricas Prometheus básicas: latência por endpoint, profundidade de fila Celery, taxa de erro por regra
  - AC: endpoint `/metrics` exposto; alertas configurados para p95 > 2s e fila > 100 jobs ❌

**Arquivos afetados:** `main.py`, `api/` (novo router admin), `core/` (logging config)

**Estimativa:** P (3–4 dias)

**Prioridade:** Médio — necessário antes de ir para produção com clientes reais

---

### EPIC 19: Reordenação e Completude do Sequenciamento de Epics

**Objetivo:** Garantir que a ordem de execução das epics respeite as dependências reais descobertas na revisão arquitetural.

**Sequenciamento corrigido:**

```
EPIC 13 (Segurança crítica)
    ↓
EPIC 14 (Multi-tenancy completo)
    ↓
EPIC 15 (Parser + cruzamento SPED×XML) ←→ EPIC 16 (Tabelas de referência)
    ↓
EPIC 17 (Performance) ←→ EPIC 18 (Observabilidade)
    ↓
EPIC 1 (Completude de ingestão) → EPIC 2 (Motor de regras completo)
    ↓
EPIC 4 (Scoring) → EPIC 5 (Dashboard) → EPIC 6 (Relatórios)
    ↓
EPIC 3 (IA — só faz sentido com ≥3 meses de dados por tenant)
    ↓
EPIC 8 (Pipeline escala) → EPIC 10 (Segurança enterprise) → EPIC 12 (Legislação auto)
    ↓
EPIC 9 (API pública) → EPIC 11 (Monetização)
```

**Marcos de validação:**
- [x] **Marco 1 — Fundação segura:** EPICs 13 + 14 concluídas (2026-05-26). Critério: novo tenant criado via API tem schema isolado; nenhum CNPJ em logs; JWT seguro em produção. ✅
- [~] **Marco 2 — Regras corretas:** EPICs 15 + 16 concluídas parcialmente (2026-05-26). Critério parcialmente atendido: `nfe_cancelada_no_sped` dispara via C110; CFOPs e CSTs validados contra tabela DB. Pendente: `saida_sem_lancamento` via cruzamento SPED×XML real (requer storage de XML bruto).
- [~] **Marco 3 — Produção estável:** EPICs 17 + 18 parcialmente concluídas. Streaming upload sem OOM ✅; health check ✅; logs JSON ✅. Pendente: filas Celery separadas, cache Redis scores, Prometheus, reprocessamento admin.
- [~] **Marco 4 — MVP Dashboard + Relatórios:** EPICs 5 + 6 com escopo MVP concluído (2026-05-27). Dashboard funcionando (KPIs, alertas, drilldown); relatório PDF com narrativa IA + Excel. Pendente para MVP completo: diff visual XML, notificações, reprocessamento on-demand.

**Estimativa:** Sem esforço próprio — é um documento de sequenciamento. Custo está nas epics individuais.

**Prioridade:** Referência — consultar antes de iniciar qualquer epic
