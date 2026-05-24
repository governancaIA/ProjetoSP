# ? Como Corrigir o Erro de Build no EasyPanel

## ?? Erro Atual

```
ERROR: failed to build: dockerfile parse error on line 1: unknown instruction: Build
```

**Causa:** EasyPanel está tentando usar `EASYPANEL_CHECKLIST.md` (documentação) como Dockerfile!

---

## ? Solução em 3 Passos

### Passo 1: Acessar a App no EasyPanel

1. Ir para: https://dashboard.easypanel.io
2. Clique em seu projeto (chatwoot)
3. Clique em: **fiscalai-backend** (a app que deu erro)

### Passo 2: Corrigir Build Settings

Clique em **Settings** (engrenagem) ? **Build**

Você verá algo como:

```
Build Context:  (pode estar vazio ou com valor errado)
Dockerfile:     (AQUI está o erro)
```

**Mude para EXATAMENTE ISSO:**

```
Build Context:    .
Dockerfile:       backend/Dockerfile
```

?? **IMPORTANTE:**
- Build Context: **SEM slash**, só um ponto: `.`
- Dockerfile: **SEM `./` no início**, relativo à raiz: `backend/Dockerfile`

### Passo 3: Fazer Rebuild

Clique em: **REBUILD**

Aguarde 5-10 minutos.

---

## ?? Referência Visual

### Build Settings Correto:

```
+----------------------------------------+
¦ General                                ¦
¦ ------------------------------------   ¦
¦ Name:            fiscalai-backend      ¦
¦ Domain:          (seu domínio)         ¦
¦                                        ¦
¦ Build                                  ¦
¦ ------------------------------------   ¦
¦ Build Context:   .                     ¦  ? Ponto
¦ Dockerfile:      backend/Dockerfile    ¦  ? Sem ./
¦                                        ¦
¦ [Save] [REBUILD]                       ¦
+----------------------------------------+
```

---

## ?? Verificação

Após corrigir, verifique:

1. **Log de Build**
   - Deve começar com: `FROM python:3.12-slim`
   - NÃO deve ter erro `unknown instruction`

2. **Se Passar:**
   ```
   ? Build completed successfully
   ? Image built and pushed
   ? Container started
   ```

3. **Health Check:**
   ```bash
   curl https://fiscalai-backend.6hjchk.easypanel.host/health
   ```
   Esperado: `{"status":"healthy"}`

---

## ?? Se Ainda Falhar

### Erro: "Dockerfile not found"
- Confirmar: `backend/Dockerfile` existe no GitHub
- Fazer: `git pull origin main` no EasyPanel (automático)
- Tentar: Rebuild novamente

### Erro: "Python not found"
- Confirmar backend/Dockerfile começa com: `FROM python:3.12-slim`
- Conferir: não há typos no Dockerfile

### Erro: "requirements.txt not found"
- Conferir se `backend/requirements.txt` existe
- Dockerfile tenta: `COPY requirements.txt .`

---

## ?? Checklist Rápido

- [ ] Build Context: `.` (ponto só)
- [ ] Dockerfile: `backend/Dockerfile` (sem ./)
- [ ] GitHub tem backend/Dockerfile (? confirmado)
- [ ] Clicou REBUILD
- [ ] Logs aparecem (esperando build)
- [ ] Build completou ?
- [ ] curl /health responde

---

## ?? Próximas Ações

Após backend funcionar:

1. ? Criar Frontend App:
   - Build Context: `.`
   - Dockerfile: `frontend/Dockerfile.prod`

2. ? Configurar domains + SSL

3. ? Testar em browser

---

## ?? URLs de Referência

- Dashboard: https://dashboard.easypanel.io
- Backend (quando pronto): https://fiscalai-backend.6hjchk.easypanel.host/health
- Frontend (quando pronto): https://fiscalai.6hjchk.easypanel.host
