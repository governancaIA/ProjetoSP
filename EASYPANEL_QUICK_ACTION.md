# ⚡ QUICK ACTION CARD — Quando o Build Acabar

> Imprima isto ou cole num bloco de notas. Quando o frontend terminar de buildar, siga EXATAMENTE estes passos.

---

## 🔴 QUANDO VER: "Build completed successfully" (Frontend)

### PASSO 1: Backend Domain (2 min)

```
1. Vá para: EasyPanel Dashboard → fiscalai-backend
2. Clique em: DOMAINS (lado direito)
3. Clique em: + Add Domain
4. Preencha:
   Domain: fiscalai-backend.6hjchk.easypanel.host
   SSL: ☑ Let's Encrypt
5. Clique em: SAVE
```

✅ Certificado vai gerar em ~30 segundos

---

### PASSO 2: Frontend Domain (2 min)

```
1. Vá para: EasyPanel Dashboard → fiscalai-frontend
2. Clique em: DOMAINS (lado direito)
3. Clique em: + Add Domain
4. Preencha:
   Domain: fiscalai.6hjchk.easypanel.host
   SSL: ☑ Let's Encrypt
5. Clique em: SAVE
```

✅ Certificado vai gerar em ~30 segundos

---

### PASSO 3: Testar Backend (30 sec)

Em PowerShell ou terminal:

```powershell
curl -k https://fiscalai-backend.6hjchk.easypanel.host/health
```

Esperado:
```json
{"status":"healthy","service":"FiscalAI API"}
```

❌ **Se falhar:** Aguarde 30 segundos e tente novamente

---

### PASSO 4: Testar Frontend (30 sec)

Em PowerShell:

```powershell
curl -k https://fiscalai.6hjchk.easypanel.host/health
```

Esperado:
```json
{"status":"healthy","service":"FiscalAI Frontend"}
```

---

### PASSO 5: Abrir no Browser (1 min)

```
1. Abrir navegador
2. Colar: https://fiscalai.6hjchk.easypanel.host
3. Pressionar ENTER
```

✅ **Deve aparecer: Página de LOGIN com email + password**

---

## 🎯 CHECKLIST FINAL

- [ ] Backend domain adicionado
- [ ] Frontend domain adicionado
- [ ] Certificados gerados (esperar 30 sec)
- [ ] Backend `/health` retorna JSON
- [ ] Frontend `/health` retorna JSON
- [ ] Browser abre e mostra página de login
- [ ] Sem erros no console do navegador (F12)

---

## 🚀 PRONTO!

Se todos os passos acima funcionarem, FiscalAI está em PRODUÇÃO!

**URLs finais:**
```
Frontend:    https://fiscalai.6hjchk.easypanel.host
Backend:     https://fiscalai-backend.6hjchk.easypanel.host
API Docs:    https://fiscalai-backend.6hjchk.easypanel.host/docs
```

---

## ❌ Se Algo Falhar

### "Connection refused" em curl
→ Espere mais 30 segundos (SSL ainda gerando)

### Frontend mostra página em branco
→ Abra F12 → Console e procure por erros vermelhos
→ Procure em `EASYPANEL_TROUBLESHOOT.md`

### 401 Unauthorized no login
→ Usuário não existe no banco
→ Tente: `test@example.com` / `test_password_123`

### CORS error no console
→ Backend `CORS_ORIGINS` env var está errado
→ Verificar em EasyPanel → fiscalai-backend → Settings

---

## 📚 Documentação Completa

- Problemas detalhados: `EASYPANEL_TROUBLESHOOT.md`
- Setup manual: `EASYPANEL_MANUAL_SETUP.md`
- Deploy local: `DOCKER_SETUP.md`

---

**Boa sorte! 🎉**
