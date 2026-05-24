# FiscalAI — Arquitetura de Produto: EPICs Completas

---

### EPIC 1: Ingestão e Parsing de Arquivos Fiscais

**Objetivo de negócio:** Eliminar o processo manual de importação e normalização de arquivos fiscais (SPED EFD ICMS/IPI, EFD Contribuições, XML NF-e, CT-e, NFS-e), que hoje consome horas de analistas e é fonte de erros de truncamento/digitação.

**Valor entregue:** Cliente sobe meses de arquivos fiscais em minutos, com garantia de integridade — reduzindo setup de auditoria de dias para horas.

**Escopo técnico:**
- [ ] Upload de arquivos via UI (drag-and-drop) e API REST com suporte a lotes (zip, múltiplos arquivos)
  - AC: arquivos de até 2 GB aceitos; progresso exibido em tempo real; checksum SHA-256 validado no servidor
- [ ] Parser de SPED EFD ICMS/IPI (blocos 0, C, D, E, G, H, K)
  - AC: registros C100, C170, D100, E110 extraídos sem perda; registros desconhecidos logados como warnings
- [ ] Parser de EFD Contribuições (blocos 0, A, C, D, F, M, P, 1)
  - AC: registros M100, M200, M400, M500 extraídos com PIS/COFINS por CST
- [ ] Parser de XML NF-e (schema v4.0) e CT-e (schema v3.0)
  - AC: parse de chave de acesso, emitente, destinatário, itens, impostos, status de cancelamento e protocolo de autorização
- [ ] Detecção automática de tipo e versão do arquivo
  - AC: classificação correta em >99% dos casos com base em header e estrutura
- [ ] Armazenamento normalizado em PostgreSQL (modelo canônico de documentos fiscais)
  - AC: dados brutos preservados em object storage (S3/MinIO); dados estruturados indexados para queries analíticas
- [ ] Reprocessamento on-demand de arquivos já importados
  - AC: novo parse não duplica dados; versão anterior marcada como superseded com audit trail

**Stack envolvida:** Python (lxml, xmltodict, pandas para EFD), FastAPI, Celery, PostgreSQL, MinIO/S3, Redis

**Dependências:** EPIC 8 (pipeline assíncrono), EPIC 7 (multi-tenancy)

**Estimativa:** G

**Prioridade:** MVP

---

### EPIC 2: Motor de Validação e Regras Fiscais

**Objetivo de negócio:** Codificar o conhecimento tributário brasileiro como regras executáveis — substituindo o analista fiscal que valida manualmente centenas de campos contra IN RFB, COTEPE, CONFAZ e ADE Cotec.

**Valor entregue:** Validação consistente, auditável e sempre atualizada — sem depender de expertise individual de cada cliente.

**Escopo técnico:**
- [ ] Engine de regras baseada em DAG de validações com versionamento semântico
  - AC: regras habilitadas/desabilitadas por tenant; resultado de cada regra logado individualmente com versão
- [ ] Regra: NF-e escriturada vs XML — divergência de valor total, base de cálculo, alíquota
  - AC: diferença >R$0,01 gera alerta; tolerância configurável por tenant
- [ ] Regra: notas canceladas (evento 110111) ainda presentes no SPED
  - AC: cruzamento de evento de cancelamento com C100/C170; qualquer nota cancelada escriturada gera alerta CRÍTICO
- [ ] Regra: nota de saída sem lançamento correspondente no livro fiscal
  - AC: toda NF-e autorizada de saída deve ter registro C100 correspondente no EFD do período
- [ ] Regra: CT-e cancelado escriturado indevidamente
  - AC: cruzamento D100 com eventos de cancelamento CT-e
- [ ] Regra: divergência de ICMS entre calculado e declarado
  - AC: tolerância de R$0,50 por item; considera diferimento, ST e isenções por CFOP/CST
- [ ] Regra: PIS/COFINS — CST incompatível com regime tributário do emitente
  - AC: Lucro Presumido não pode usar CST 01/02/03; Simples Nacional não escritura PIS/COFINS
- [ ] Regra: IPI — alíquota divergente da TIPI para o NCM declarado
  - AC: integração com tabela TIPI vigente; atualização mensal automática
- [ ] Regra: CFOP inválido para operação (UF origem vs destino, natureza)
  - AC: validação de CFOP inter/intraestadual; CFOP de devolução exige NF referenciada

**Stack envolvida:** Python (pydantic para schemas de regras), PostgreSQL (tabelas TIPI, CFOP, CST), Redis (cache de referências), Celery

**Dependências:** EPIC 1 (dados normalizados), EPIC 4 (scoring consome output das regras)

**Estimativa:** G

**Prioridade:** MVP

---

### EPIC 3: Detecção de Inconsistências com IA e Heurísticas

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

### EPIC 4: Scoring de Risco Fiscal e Classificação de Severidade

**Objetivo de negócio:** Transformar centenas de alertas brutos em visão priorizada de risco — para que o analista saiba exatamente onde agir primeiro, sem vasculhar planilhas.

**Valor entregue:** Reduz tempo de triagem de horas para minutos; priorização por impacto financeiro real.

**Escopo técnico:**
- [ ] Modelo de scoring por alerta (CRÍTICO / ALTO / MÉDIO / BAIXO / INFORMATIVO)
  - AC: CRÍTICO = potencial multa >R$10k ou irregularidade dolosa; BAIXO = divergência <R$100; critérios configuráveis por tenant
- [ ] Score de risco agregado por período (competência mensal), escala 0–100
  - AC: histórico de evolução exibido em gráfico de tendência; delta entre períodos com causa raiz
- [ ] Score consolidado para grupos econômicos com múltiplos CNPJs
  - AC: visão agregada quando tenant tem múltiplos CNPJs cadastrados
- [ ] Estimativa de exposição financeira por inconsistência (tabela de penalidades)
  - AC: cálculo baseado em art. 12 DL 1598 e Portaria CAT; exibido em R$
- [ ] Priorização automática de fila de trabalho
  - AC: fila ordenada por (severidade × exposição financeira × probabilidade de autuação)

**Stack envolvida:** Python (lógica de scoring), PostgreSQL, FastAPI

**Dependências:** EPIC 2 (alertas de regras), EPIC 3 (alertas de IA)

**Estimativa:** M

**Prioridade:** MVP

---

### EPIC 5: Dashboard Executivo e Visualização de Alertas

**Objetivo de negócio:** Dar ao CFO, controller e analista fiscal uma visão unificada e interativa — tornando a plataforma o centro de comando da saúde fiscal da empresa.

**Valor entregue:** Visibilidade imediata do risco sem precisar de analista intermediário para interpretar dados brutos.

**Escopo técnico:**
- [ ] Dashboard home: score atual, evolução 12 meses, top-5 inconsistências críticas
  - AC: carregamento <2s; dados atualizados após cada processamento de arquivo
- [ ] Tela de alertas com filtros avançados (severidade, tipo, período, CNPJ, valor)
  - AC: filtros combinados; paginação de até 10k alertas sem degradação; exportação da lista filtrada
- [ ] Drilldown de alerta: diff visual XML original vs dado escriturado
  - AC: lado a lado com diferença destacada em vermelho; clique abre XML completo
- [ ] Visão por fornecedor: histórico de inconsistências e score de confiabilidade
  - AC: ranking de fornecedores por número/valor de inconsistências; gráfico de tendência
- [ ] Heatmap de risco fiscal por competência (calendário 12 meses)
  - AC: cor proporcional ao score; click abre detalhes do período
- [ ] Notificações in-app e email para alertas CRÍTICOS
  - AC: disparo em <5min após detecção; configurável por usuário

**Stack envolvida:** React + TypeScript, Recharts/Victory (gráficos), FastAPI (BFF), PostgreSQL

**Dependências:** EPIC 4 (scores e alertas), EPIC 7 (auth e multi-tenancy)

**Estimativa:** G

**Prioridade:** MVP

---

### EPIC 6: Relatórios e Exportação (PDF, Excel, Auditoria Rastreável)

**Objetivo de negócio:** Viabilizar que os resultados da plataforma sejam usados em defesas fiscais, reuniões com auditores da Receita e apresentações para board — onde credibilidade do dado é tão importante quanto o dado.

**Valor entregue:** Relatório auditável substitui horas de formatação manual; evidência estruturada reduz custo de defesa em auto de infração.

**Escopo técnico:**
- [ ] Relatório executivo PDF: sumário de risco, top inconsistências, score, hash de integridade
  - AC: gerado em <30s para até 6 meses de dados; inclui hash SHA-256 do arquivo de origem
- [ ] Relatório detalhado por tipo de inconsistência (Excel/CSV)
  - AC: aba por tipo de regra; cada linha com NF, campo divergente, valor esperado, valor encontrado, exposição estimada
- [ ] Exportação de trilha de auditoria completa (imutável, com IP e timestamp UTC)
  - AC: log de todas as ações do usuário exportável em CSV
- [ ] Relatório comparativo entre períodos (mês a mês, ano a ano)
  - AC: delta de inconsistências entre dois períodos; evolução de exposição financeira
- [ ] Agendamento de relatórios periódicos (mensal automático D+5)
  - AC: relatório gerado automaticamente no D+5 após fechamento da competência; enviado por email em PDF

**Stack envolvida:** Python (WeasyPrint/ReportLab para PDF, openpyxl para Excel), Celery, S3/MinIO

**Dependências:** EPIC 4, EPIC 5 (mesmos dados, formato diferente)

**Estimativa:** M

**Prioridade:** MVP (PDF básico + CSV); Fase 2 (agendamento + comparativos)

---

### EPIC 7: Multi-tenancy, Autenticação e Controle de Acesso

**Objetivo de negócio:** Suportar múltiplos clientes com isolamento total de dados e controle granular de permissões — requisito obrigatório para SaaS B2B com dados fiscais sensíveis.

**Valor entregue:** Segurança e compliance nativos — isolamento técnico auditável sem depender de "confiar na palavra" da plataforma.

**Escopo técnico:**
- [ ] Multi-tenant com schema isolation no PostgreSQL (RLS habilitado, schema por tenant)
  - AC: query sem WHERE de tenant_id retorna vazio; schemas completamente isolados entre tenants
- [ ] Autenticação JWT + refresh token com rotação
  - AC: access token TTL 15min; refresh token TTL 7 dias; revogação imediata por logout
- [ ] SSO/SAML 2.0 para enterprise (Azure AD, Okta)
  - AC: login via IdP externo; provisionamento automático no primeiro login
- [ ] RBAC: Admin, Analista Fiscal, Controller, Auditor Externo (read-only)
  - AC: Auditor Externo não exporta dados brutos; Admin convida usuários; permissões configuráveis
- [ ] Suporte a múltiplos CNPJs por tenant (grupos econômicos)
  - AC: N CNPJs por tenant; usuário com acesso a subconjunto; visão consolidada para Admin
- [ ] Wizard de onboarding de tenant (regime tributário, CNPJs, período inicial)
  - AC: configuração em <10min; CNPJ validado via Receita Federal

**Stack envolvida:** FastAPI + python-jose (JWT), PostgreSQL (RLS + schemas), python-saml / authlib (SSO)

**Dependências:** Fundação para todas as outras EPICs

**Estimativa:** G

**Prioridade:** MVP

---

### EPIC 8: Pipeline Assíncrono e Processamento Escalável

**Objetivo de negócio:** Garantir que processamento de arquivos grandes (SPED de 500k NFs/mês) não trave a plataforma nem degrade a experiência de outros tenants.

**Valor entregue:** SLA de processamento previsível; plataforma não degrada sob carga; custo de infra escala proporcionalmente ao uso.

**Escopo técnico:**
- [ ] Filas com Celery + Redis (filas separadas: urgent / normal / bulk)
  - AC: job de parsing de arquivo grande não bloqueia jobs de dashboard; filas monitoradas via Flower
- [ ] Workers auto-scaling baseado em profundidade de fila (K8s HPA)
  - AC: profundidade >100 jobs dispara scale-out; idle >5min dispara scale-in; tempo de scale <2min
- [ ] Chunking de arquivos grandes (SPED >500MB processado em chunks paralelos)
  - AC: resultado consolidado sem duplicatas
- [ ] Retry com backoff exponencial (máx. 3 tentativas: 1min/5min/15min)
  - AC: falha definitiva notifica o usuário
- [ ] Dead letter queue (DLQ) com reprocessamento manual via painel admin
  - AC: jobs em DLQ visíveis; reprocessamento com 1 clique
- [ ] Rate limiting por tenant para uploads
  - AC: plano básico 10 uploads/dia, 100MB/arquivo; enterprise ilimitado com throttling

**Stack envolvida:** Celery, Redis, Docker, Kubernetes (HPA), Flower

**Dependências:** Base para EPICs 1, 2, 3

**Estimativa:** M

**Prioridade:** MVP

---

### EPIC 9: API Pública e Integrações com ERPs

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

### EPIC 10: Segurança, LGPD e Observabilidade

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

### EPIC 11: Onboarding, Planos e Monetização SaaS

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

### EPIC 12: Atualização Automática de Legislação Fiscal

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
