# 🚀 FiscalAI no EasyPanel — Guia Rápido

**Seu projeto está pronto para rodar na nuvem!**

---

## ⚡ 30 Segundos

1. **GitHub Push**
   ```powershell
   git push origin main
   ```

2. **EasyPanel Dashboard** → Crie 2 apps:
   - Backend: `./backend/Dockerfile`
   - Frontend: `./frontend/Dockerfile.prod`

3. **Crie 3 serviços:**
   - PostgreSQL
   - Redis
   - MinIO

4. **Adicione variáveis de ambiente** (template em `infra/REFERENCE_VARS.md`)

5. **Aguarde builds → Teste URLs**

✅ **Pronto!** FiscalAI está no ar.

---

## 📚 Documentação Completa

| Documento | Quando Usar |
|---|---|
| **[QUICKSTART_EASYPANEL.md](infra/QUICKSTART_EASYPANEL.md)** | Primeira vez setup (5 passos) |
| **[CHECKLIST_DEPLOY.md](infra/CHECKLIST_DEPLOY.md)** | Segue durante deploy (passo-a-passo clicável) |
| **[REFERENCE_VARS.md](infra/REFERENCE_VARS.md)** | Copia/cola variáveis de ambiente |
| **[EASYPANEL_SETUP_GUIA.md](infra/EASYPANEL_SETUP_GUIA.md)** | Guia completo com troubleshooting |
| **[EASYPANEL_ARQUITETURA.md](infra/EASYPANEL_ARQUITETURA.md)** | Entender como funciona tudo junto |

---

## 🎯 O que você vai ter no final

```
https://chatwoot-fiscalai-frontend.6hjchk.easypanel.host/
↓
[React Frontend + Vite] → Upload SPED/XML
                      ↓
https://chatwoot-fiscalai-backend.6hjchk.easypanel.host/
↓
[FastAPI Backend] → Valida, executa regras
                 ↓
[PostgreSQL] + [Redis] + [MinIO]
↓
Dashboard com inconsistências fiscais detectadas
```

---

## 🛠️ Stack Técnica

| Componente | Tech | Status |
|---|---|---|
| Frontend | React + Vite + Tailwind | ✅ Pronto |
| Backend | FastAPI + Celery | ✅ Pronto |
| Database | PostgreSQL | ✅ Managed |
| Cache | Redis | ✅ Managed |
| Storage | MinIO (S3) | ✅ Pronto |
| SSL | Let's Encrypt | ✅ Automático |

---

## ❓ FAQ

**P: Quanto custa?**  
A: ~$30-150/mês (depende de uso). Upgradável conforme cresce.

**P: Preciso fazer algo de especial no código?**  
A: Não! Docker + variáveis de ambiente. Tudo pronto.

**P: E se der erro?**  
A: Veja `EASYPANEL_SETUP_GUIA.md` seção "Troubleshooting". Ou checklist: `CHECKLIST_DEPLOY.md`

**P: Posso migrar para AWS/GCP depois?**  
A: Sim! Terraform pronto em `infra/terraform/` (Fase 2).

**P: Backup dos dados?**  
A: EasyPanel oferece backups automáticos. Configure no dashboard.

---

## 🚀 Começa Agora

**Pré-requisitos:**
- GitHub com repo sincronizado ✅
- Acesso ao EasyPanel ✅
- 30 min livres ⏱️

**Próximo passo:**
- Abra [QUICKSTART_EASYPANEL.md](infra/QUICKSTART_EASYPANEL.md)
- Siga os 5 passos
- Done! 🎉

---

**Perguntas?** Ver todos os documentos em [`infra/`](infra/)

