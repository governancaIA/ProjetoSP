# FiscalAI — Roadmap de Entregas

> URL dev: `chatwoot-fiscalai-frontend.6hjchk.easypanel.host`
> Atualizado: 2026-05-25

---

## Sprint 0 — Estabilização (DONE ✅)

**Objetivo:** Fazer o que já existe funcionar corretamente em produção.

| # | Item | Arquivo | Status |
|---|---|---|---|
| B1 | Import de `fiscal_rules` em `validate_document.py` | `backend/app/tasks/validate_document.py` | ✅ |
| B2 | Linkagem C170→C100 correta no SPED parser | `backend/app/parsers/sped_efd_icms.py` + `document_service.py` | ✅ |
| B3 | `isAuthenticated` false no page reload | `frontend/src/contexts/AuthContext.tsx` | ✅ |

**Resultado:** Pipeline upload→parse→validação→scoring funciona end-to-end.

---

## Epic A — Upload de Arquivo (Frontend)

**Objetivo:** Usuário consegue subir arquivos fiscais pela UI.
**Bloqueia:** Todos os outros épicos — sem upload, o dashboard está sempre vazio.
**Estimativa:** 1 dia

### Entregas

| # | Tarefa | Detalhes |
|---|---|---|
| A1 | Componente `UploadZone` (drag-and-drop) | Aceita `.txt`, `.xml`, `.zip`; valida tipo e tamanho antes de enviar |
| A2 | Barra de progresso com estado | `pending` → `processing` → `completed` / `failed` |
| A3 | Polling do status do job | `GET /documents/{id}` a cada 2s até `completed` ou `failed` |
| A4 | Integração na `DocumentsPage` | Botão "Enviar Arquivo" abre modal com `UploadZone` |
| A5 | Toast de sucesso/erro | Notificação após conclusão do upload |

**Aceite:** Usuário arrasta um arquivo SPED.txt → barra de progresso → documento aparece na lista com score calculado.

---

## Epic B — Estabilização do Backend (Bugs Restantes)

**Objetivo:** Corrigir os bugs que degradam qualidade dos resultados sem quebrar o fluxo.
**Estimativa:** 1 dia

### Entregas

| # | Tarefa | Arquivo | Detalhes |
|---|---|---|---|
| B4 | `CteCanceladoRule` — tabela correta | `validators/rules/fiscal_rules.py` | Mover regra para operar sobre `CTDocument` em vez de `FiscalDocument` |
| B5 | Tenant schema criado no register | `services/auth_service.py` | Chamar `create_tenant_schema()` após criar o `User` |
| B6 | N+1 queries no `GET /documents` | `api/documents.py` + `services/scoring_service.py` | Agregar scores em query única com `JOIN` em vez de N queries |
| B7 | Alembic migrations | `migrations/versions/` | Criar migração inicial a partir do estado atual dos models |

**Aceite:** Nenhum `ERROR` nos logs do backend em fluxo normal. `GET /documents` com 50 docs: < 500ms.

---

## Epic C — Relatórios e Exportação (Epic 6)

**Objetivo:** Cliente exporta resultado da auditoria em PDF/Excel para apresentar ao contador ou fiscal.
**Estimativa:** 2-3 dias
**Valor:** Fecha venda — "me dê algo para mostrar ao cliente"

### Entregas

| # | Tarefa | Detalhes |
|---|---|---|
| C1 | Endpoint `GET /reports/period/{year}/{month}/pdf` | Gera PDF com score do período, top inconsistências, documentos críticos |
| C2 | Endpoint `GET /reports/document/{id}/pdf` | Relatório de um documento: dados da NF + resultados de todas as regras |
| C3 | Endpoint `GET /reports/period/{year}/{month}/excel` | Excel com todas as inconsistências do período, uma linha por regra |
| C4 | Serviço `ReportService` | Usa `reportlab` (PDF) + `openpyxl` (Excel); template com logo FiscalAI |
| C5 | Conectar `ReportsPage.tsx` | Botões "Baixar PDF" e "Baixar Excel" chamam endpoints reais |
| C6 | Celery task para geração assíncrona | Relatórios grandes gerados em background; link de download via polling |

**Aceite:** Clicar "Baixar PDF" → download inicia em < 5s para períodos de até 500 documentos.

---

## Epic D — Completar Motor de Regras (Epic 2)

**Objetivo:** Aumentar cobertura de inconsistências detectadas.
**Estimativa:** 2-3 dias
**Valor:** Argumento técnico de venda — "detectamos X tipos de inconsistência"

### Entregas

| # | Tarefa | Detalhes |
|---|---|---|
| D1 | `SaidaSemLancamentoRule` — implementar real | Cross-document lookup: NF-e de saída deve ter C100 no SPED do período |
| D2 | `CstIncompatiavelRule` — regime tributário | Lucro Presumido ≠ CST 01/02/03; Simples Nacional não escritura PIS/COFINS |
| D3 | `CfopInvalidoRule` — validação semântica | Inter/intraestadual por UF; CFOP devolução exige NF referenciada |
| D4 | Config de regras por tenant | Tabela `rule_configurations` no DB; tolerâncias personalizáveis por tenant |
| D5 | Endpoint `GET /rules` e `PATCH /rules/{id}` | UI para habilitar/desabilitar regras e ajustar tolerâncias |

**Aceite:** Todas as 7 regras produzem resultados reais (zero stubs). Config de tolerância por tenant funciona.

---

## Epic E — Multi-tenancy Completo (Epic 7)

**Objetivo:** Suportar múltiplos clientes reais sem risco de vazamento de dados.
**Estimativa:** 1-2 dias
**Valor:** Necessário antes de ter mais de 1 cliente em produção

### Entregas

| # | Tarefa | Detalhes |
|---|---|---|
| E1 | Schema criado no register (Bug B5 já corrigido) | `create_tenant_schema()` chamado após criar User |
| E2 | Consistência de isolamento | Padronizar para row-level filtering (`tenant_id`) em todos os endpoints; remover `set_tenant_schema()` das APIs (mantido apenas nas tasks Celery) |
| E3 | Endpoint de onboarding do tenant | `POST /tenants` para criar tenant + admin user em uma chamada |
| E4 | Middleware de tenant | Extrair `tenant_id` do JWT e setar no contexto da request automaticamente |
| E5 | Limites de storage por tenant | Quota de 10GB/tenant já existe no upload; expor uso via `GET /tenants/me/storage` |

**Aceite:** Dois tenants distintos não veem dados um do outro. Tenant novo criado em uma chamada de API.

---

## Epic F — IA e Detecção de Anomalias (Epic 3)

**Objetivo:** Detectar padrões anômalos que regras determinísticas não capturam.
**Estimativa:** 1-2 semanas
**Valor:** Diferencial competitivo e justificativa de preço premium

### Entregas

| # | Tarefa | Detalhes |
|---|---|---|
| F1 | Isolation Forest por fornecedor | Detecta NFs com valores atípicos vs histórico do fornecedor |
| F2 | Detecção de gaps em sequência de NF | Sequências de numeração com "buracos" suspeitos |
| F3 | CNPJ inapto/baixado | Cross-check CNPJ emitente contra base Receita Federal |
| F4 | Score de risco ML | Combina heurísticas + regras + anomalias em score unificado |
| F5 | Explicabilidade das anomalias | Log estruturado de "por que esta NF é suspeita" |

**Aceite:** Anomalias detectadas aparecem no dashboard com severidade e explicação. Taxa de falso positivo < 5%.

---

## Visão Geral — Ordem de Execução

```
Semana 1
├── Sprint 0 — Bugs críticos          ✅ DONE
├── Epic A   — Upload UI              → NEXT
└── Epic B   — Bugs restantes backend

Semana 2
├── Epic C   — Relatórios/Export
└── Epic D   — Motor de regras completo

Semana 3
└── Epic E   — Multi-tenancy completo

Mês 2+
└── Epic F   — IA / Anomaly Detection
```

---

## Critérios de "Pronto para Demo" no EasyPanel Dev

- [ ] **Epic A** concluída — usuário sobe arquivo e vê resultado
- [ ] **Epic B** concluída — zero erros críticos nos logs
- [ ] **Epic C** concluída — botão de exportar PDF funciona
- [ ] Backend retorna `{"status": "ok"}` no `/health`
- [ ] Frontend carrega sem erros de console
- [ ] Login, upload, dashboard e relatório funcionam end-to-end

---

## Notas Técnicas

### Stack de Relatórios (Epic C)
```python
# PDF
pip install reportlab weasyprint

# Excel
pip install openpyxl

# Alternativa tudo-em-um
pip install jinja2 xhtml2pdf
```

### Stack de IA (Epic F)
```python
pip install scikit-learn  # Isolation Forest
pip install pandas numpy  # Manipulação de dados
pip install sentence-transformers  # Embeddings (futuro RAG)
```

### Tabelas novas necessárias

| Epic | Tabela | Motivo |
|---|---|---|
| B7 | Migração Alembic | Versionamento do schema |
| D4 | `rule_configurations` | Config de regras por tenant |
| E3 | `tenants` | Registro formal de tenants |
| F1 | `anomaly_results` | Log de anomalias ML |
