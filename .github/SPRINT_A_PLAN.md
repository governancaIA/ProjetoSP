# Sprint A — Plano de Conclusão

## Tarefas Identificadas

### ✅ Já Completo
- UploadZone component (drag-and-drop)
- DocumentsPage integração
- API uploadFiles() com progress
- Backend /uploads endpoint com job_id
- Backend /jobs/{job_id} polling endpoint

### 🟡 Faltando

**A3 - Polling Logic** (Frontend)
- Implementar hook `useJobPolling(job_id)` para polling a cada 2s
- Quando status = 'completed' ou 'failed', parar polling
- Integrar no UploadZone para aguardar processamento

**A5 - Toast Notifications** (Frontend)
- Adicionar biblioteca de toast (sonner ou react-toastify)
- Toast de sucesso ao upload completo
- Toast de erro com mensagem do servidor
- Toast de progresso "Processando documento..."

**Backend Test**
- Testar se upload endpoint retorna job_id correto
- Verificar se status do documento é atualizado no polling

---

## Sequência de Implementação

```
1. Implementar useJobPolling hook
2. Integrar polling no UploadZone
3. Adicionar Toast notifications
4. Testar end-to-end (upload → processing → done)
```

**Tempo estimado:** 30-45 min
