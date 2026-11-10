# Implantação em produção

Este guia põe o Salão em Dia no ar num servidor Linux com Docker. Um único
`docker compose up` sobe tudo: banco, migrações, API e o site, com HTTPS automático.
O que depende de escolhas suas (hospedagem, domínio, contas externas) está marcado com
**[decisão externa]**.

Os comandos foram executados num ambiente local de teste (ver
`RELATORIO_REVISAO_E_DEPLOY.md`), com `DOMINIO=localhost`. Com um domínio público, o passo
que muda é o certificado: o Let's Encrypt só o emite com o DNS já apontando para o servidor.

---

## 1. O que sobe

```
navegador ──HTTPS──▶ web (Caddy, portas 80/443) ──┬─▶ site estático (dentro do contêiner)
celular   ──HTTPS──▶        mesmo domínio          └─▶ /api/ ──▶ api (FastAPI) ──▶ db (PostgreSQL 16)
                                                                      └─▶ volume de imagens (ou S3)
```

| Serviço | O que faz | Guarda dados? |
| --- | --- | --- |
| `db` | PostgreSQL 16, sem porta publicada | **sim**: volume `dados_postgres` (tudo do sistema) |
| `migrar` | aplica as migrações do banco e termina, a cada subida | não |
| `api` | a API, sem porta publicada (só o `web` chega nela) | **sim**: volume `dados_imagens` (fotos dos clientes) |
| `web` | Caddy: entrega o site, encaminha `/api/` para a API, obtém e renova o certificado HTTPS | volume `caddy_dados` (certificados) |

O aplicativo de celular não roda no servidor: ele é gerado para as lojas e aponta para
`https://SEU-DOMINIO` (seção 9).

## 2. Pré-requisitos

- **Servidor Linux** com IP público e acesso SSH **[decisão externa: provedor]**. Qualquer VPS
  serve (Hetzner, DigitalOcean, Contabo, Hostinger, AWS Lightsail, Oracle Cloud...).
  Ponto de partida: 2 vCPU, 4 GB de RAM (a detecção de rosto usa OpenCV e o build do site
  usa Node), 40 GB de disco.
- **Docker Engine 24+ com o plugin Compose v2.20+** no servidor
  (`curl -fsSL https://get.docker.com | sh` instala os dois no Ubuntu/Debian).
- **Um domínio** (ex.: `salao.seudominio.com.br`) com um registro DNS do tipo **A**
  apontando para o IP do servidor **[decisão externa]**.
- **Portas 80 e 443 liberadas** no firewall do servidor e no painel do provedor.
- **Chave da Replicate** (`r8_...`) para a simulação real **[decisão externa]**.
- Opcionais: credenciais do Google (login com Google), bucket S3 para as imagens.

## 3. Configuração (`.env`)

Na raiz do projeto, no servidor:

```bash
cp .env.example .env
chmod 600 .env
```

Preencha no `.env`:

| Variável | Valor |
| --- | --- |
| `DOMINIO` | o domínio, sem `https://` (ex.: `salao.seudominio.com.br`) |
| `POSTGRES_PASSWORD` | gere com `openssl rand -hex 24` |
| `JWT_SECRET` | gere com `openssl rand -hex 32` (nunca reaproveite o de outro ambiente) |
| `AI_PROVIDER` | `replicate` |
| `AI_API_KEY` | a chave da Replicate |

O resto já tem padrão; [`.env.example`](.env.example) explica cada variável. Sem
`DOMINIO`, `POSTGRES_PASSWORD` ou `JWT_SECRET`, o compose recusa subir e diz qual falta.
A API também se recusa a subir com configuração insegura de produção (modo demonstração,
banco de desenvolvimento, CORS aberto).

**Login com Google (opcional):** preencha `GOOGLE_CLIENT_IDS` e
`EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` com o mesmo ID de cliente web e cadastre o endereço do
site no Google Cloud. O passo a passo, com os erros mais comuns, está em
[`docs/GUIA_LOGIN_GOOGLE.md`](docs/GUIA_LOGIN_GOOGLE.md), seção 4. Sem as duas variáveis o
botão não aparece e o login por e-mail e senha segue igual.

Segredos ficam só nesse `.env` do servidor: não vão para o Git, para as imagens Docker nem
para o aplicativo.

## 4. Primeira subida

```bash
docker compose up -d --build --wait
```

O que acontece, em ordem e sem esperas artificiais: as imagens são construídas (a primeira
vez leva alguns minutos: o site é compilado dentro do Docker) → `db` fica saudável →
`migrar` cria o banco e termina → `api` sobe e só é dada como pronta quando
`/api/v1/saude` responde → `web` sobe e pede o certificado ao Let's Encrypt.

O `--wait` termina com erro se algum serviço não ficar pronto. Para ver o estado e os logs:

```bash
docker compose ps
docker compose logs --tail=100 web api
```

Atrás de um proxy corporativo que inspeciona TLS (raro em servidor), entregue a CA aos
builds: `docker build --secret id=ca,src=/caminho/ca.crt ...` (ver os Dockerfiles).

## 5. Conferir depois de subir

```bash
D=https://salao.seudominio.com.br
curl -fsS $D/api/v1/saude                                  # {"ok":true,"ambiente":"producao"}
curl -fsS -o /dev/null -w '%{http_code}\n' $D/             # 200 (site)
curl -fsS -o /dev/null -w '%{http_code}\n' $D/agenda       # 200 (rota interna do site)
curl -s -o /dev/null -D - $D/api/v1/catalogo | grep -i strict-transport   # HSTS presente
docker compose logs --tail=50 api                          # JSON; avisos de produção conferidos
```

Com `AI_PROVIDER=replicate`, confira os modelos sem gastar crédito:

```bash
docker compose exec api python -m app.diagnostico_ia
```

Depois, pelo navegador em `https://SEU-DOMINIO`: criar a conta, cadastrar um cliente,
registrar o consentimento, enviar uma foto, gerar uma simulação, agendar e trocar a senha.

**Se o certificado não sair** (o navegador acusa conexão não segura): confira se o DNS já
aponta para o servidor (`dig +short SEU-DOMINIO`), se as portas 80 e 443 estão abertas, e
leia `docker compose logs web`. O Caddy tenta de novo sozinho.

**Testar na própria máquina antes:** `DOMINIO=localhost` sobe tudo com um certificado local
(o navegador avisa que não é confiável; aceite para testar) em `https://localhost`.

## 6. Atualizar para uma versão nova

```bash
./scripts/backup_producao.sh /caminho/seguro/backups   # 1. backup antes de tudo
git pull                                                # 2. (ou copie os arquivos novos)
export VERSAO=$(date +%Y%m%d-%H%M)                      # 3. etiqueta para poder voltar
docker compose up -d --build --wait                     # 4. constrói, migra e troca os contêineres
```

As migrações rodam uma vez por subida, no serviço `migrar`, e esperam uma trava no banco
(duas execuções simultâneas não se atropelam). Nenhuma migração apaga dados na subida.

Durante a troca da `api` há alguns segundos sem resposta (uma instância só). O Docker
espera até 160 s para simulações em andamento terminarem; uma interrompida aparece como
falha ("interrompida") e pode ser gerada de novo.

## 7. Backup e restauração

**O que precisa de backup:** o banco e as fotos, **juntos** (um banco restaurado sem as fotos
mostra "Imagem indisponível"). Os certificados (`caddy_dados`) o Caddy obtém de novo
sozinho.

```bash
./scripts/backup_producao.sh /caminho/seguro/backups
# gera banco-AAAAmmdd-HHMMSS.dump e imagens-AAAAmmdd-HHMMSS.tar.gz e confere o dump
```

Agende (cron diário) e copie os arquivos para **fora do servidor**, criptografados: contêm
dados pessoais e fotos de rosto. **[decisão externa: destino e retenção]**

```
15 3 * * * cd /srv/salao-em-dia && ./scripts/backup_producao.sh /srv/backups >> /var/log/salao-backup.log 2>&1
```

**Restaurar** (substitui o banco atual: confira o backup antes):

```bash
docker compose stop api web
docker compose exec -T db dropdb -U espelho espelho
docker compose exec -T db createdb -U espelho espelho
docker compose exec -T db pg_restore -U espelho -d espelho --no-owner --exit-on-error < banco-AAAAmmdd-HHMMSS.dump
docker compose run --rm -T --no-deps --entrypoint tar api xzf - -C /app/dados < imagens-AAAAmmdd-HHMMSS.tar.gz
docker compose up -d --wait
```

A extração grava por cima do volume: fotos enviadas **depois** do backup continuam no disco,
sem registro que as encontre. Para não deixá-las órfãs (dados pessoais), esvazie o volume
`dados_imagens` antes de extrair, à mão e depois de conferir o backup.

Para ensaiar sem risco, restaure num banco de outro nome (`createdb ... espelho_teste` e
`pg_restore -d espelho_teste`) e compare as contagens das tabelas.

## 8. Voltar para a versão anterior (rollback)

Cada build fica etiquetado com `VERSAO`. Para voltar:

```bash
export VERSAO=<etiqueta-anterior>
docker compose up -d --no-build --wait api web
```

Reverter o código **não** reverte o banco. Regra do projeto: toda migração precisa
funcionar com o código da versão anterior (por isso o rollback do código basta). As
migrações desta versão seguem a regra (conferido rodando a API anterior sobre o banco
migrado). Se uma versão futura quebrar a regra, o caminho é restaurar o backup feito antes
da atualização (seção 7), perdendo o que foi gravado depois.

## 9. Aplicativo de celular (lojas)

**[decisão externa]** Exige conta Expo/EAS e contas de desenvolvedor Google Play (Android) e
Apple (iOS).

```bash
cd espelho
npm ci
npx eas-cli login
npx eas-cli build:configure                      # cria o eas.json (o projeto ainda não tem)
```

Defina `EXPO_PUBLIC_API_URL=https://SEU-DOMINIO` (e os `EXPO_PUBLIC_GOOGLE_*`, se usar o
login com Google) nas variáveis de ambiente do EAS, e gere:

```bash
npx eas-cli build --platform android             # ou ios
```

A URL precisa ser https: o Android recusa HTTP em builds de produção. Sem ela, o aplicativo
avisa que foi gerado sem o endereço do servidor.

### APK para instalar direto (sem loja)

O `espelho/eas.json` tem o perfil `apk`, com o endereço do servidor e os IDs do Google já
preenchidos (todos públicos; nenhum segredo vai no aplicativo). Gera um `.apk` que se
instala baixando o arquivo no celular, sem conta na Google Play:

```bash
cd espelho
npx eas-cli@25.2.0 login
npx eas-cli@25.2.0 build --platform android --profile apk
```

Na primeira vez, o EAS pergunta se pode criar o projeto na sua conta e gerar a chave de
assinatura do Android: responda que sim. Guarde a chave no EAS (o padrão): todas as
versões seguintes precisam ser assinadas por ela para instalar por cima da anterior.

O botão do Google no Android só aparece com `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID`
preenchido: crie o cliente Android (docs/GUIA_LOGIN_GOOGLE.md, seção 2, item 4) com a
SHA-1 mostrada por `npx eas-cli@25.2.0 credentials --platform android`, acrescente
`"EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID": "<ID>"` ao `env` do perfil no `eas.json` (o EAS
recusa valor vazio, por isso a linha não existe antes), acrescente-o ao `GOOGLE_CLIENT_IDS` do servidor e gere o APK de novo.

## 10. Operação

- **Sondas:** `GET /api/v1/saude/vivo` (o processo responde) e `GET /api/v1/saude`
  (pronta: banco acessível e migrações aplicadas; 503 se não). Aponte um monitor externo
  para `https://SEU-DOMINIO/api/v1/saude` **[decisão externa]**.
- **Logs:** `docker compose logs -f api web`. A API escreve JSON por linha, com o
  identificador da requisição (o mesmo do cabeçalho `X-Request-ID`); a query das imagens
  (que dá acesso à foto) não vai para o log. Rotação: 5 × 20 MB por contêiner.
- **Reiniciar:** `docker compose restart api`. Os serviços voltam sozinhos se caírem e
  quando o servidor reinicia (`restart: unless-stopped`).
- **Sessões:** no aplicativo, Perfil → "Senha e sessões" troca a senha e encerra os outros
  aparelhos. Trocar o `JWT_SECRET` desconecta todas as contas.
- **Custo da IA:** `SIMULACAO_MAX_POR_HORA` por conta, mais o limite de gasto que a
  própria Replicate permite configurar **[decisão externa]**.
- **Escala:** `WEB_CONCURRENCY` controla os processos da API. O freio de tentativas de login
  é em memória, por processo.

## 11. Variações

- **Porta 443 ocupada por outro sistema (site numa porta alternativa, ex.: 9443):** a porta
  80 precisa estar livre (o certificado é validado por ela). No `.env`:

  ```
  PORTA_HTTP=80
  PORTA_HTTPS=9443
  PORTA_HTTPS_INTERNA=9443
  URL_PUBLICA=https://SEU-DOMINIO:9443
  CORS_ORIGENS=https://SEU-DOMINIO:9443
  ```

  O site fica em `https://SEU-DOMINIO:9443`, e o acesso precisa ser sempre por esse endereço
  completo: quem digita o domínio sem a porta cai na 443, que é o outro sistema (o
  redirecionamento de `http://` também vai sem a porta). No app de celular,
  `EXPO_PUBLIC_API_URL=https://SEU-DOMINIO:9443`.
- **Portas 80 e 443 usadas por um servidor web que já existe (Nginx, Apache...):** ele cuida
  do HTTPS e encaminha para o projeto. No `.env`: `DOMINIO=http://SEU-DOMINIO` (o `http://`
  faz o Caddy do projeto não pedir certificado), `URL_PUBLICA` e `CORS_ORIGENS` com
  `https://SEU-DOMINIO`, `PORTA_HTTP=127.0.0.1:8080` e `PORTA_HTTPS=127.0.0.1:8443`; no
  servidor web, encaminhe o domínio para `http://127.0.0.1:8080` com
  `client_max_body_size 12m` e 180 s de tempo limite. Acrescente também
  `PROXIES_CONFIAVEIS=private_ranges`: sem ela, o freio de login veria todos os usuários
  pelo endereço do servidor web (as portas em `127.0.0.1` garantem que só ele chega aqui).
- **Proxy de outro sistema rodando em Docker (Caddy, Traefik...) com as portas 80 e 443:**
  o proxy cuida do domínio e do HTTPS (inclusive com certificado por DNS-01) e alcança o
  site pela rede Docker, sem porta publicada. Use o `docker-compose.proxy.yml`. No `.env`:

  ```
  COMPOSE_FILE=docker-compose.yml:docker-compose.proxy.yml
  REDE_PROXY=nome-da-rede-docker-do-proxy
  DOMINIO=salao.dominio-do-proxy.com.br
  ```

  Sem `URL_PUBLICA` nem `CORS_ORIGENS`: elas saem do `DOMINIO` (`https://DOMINIO`), sem
  porta. Com o `COMPOSE_FILE`, os comandos continuam os mesmos (`docker compose up -d
  --build --wait`). No proxy, o subdomínio encaminha para `salao-em-dia-web:80`, com corpo
  de até 12 MB e 180 s de tempo limite. Exemplo para Caddy:

  ```
  salao.dominio-do-proxy.com.br {
  	# tls: o mesmo usado nos outros sites do proxy (DNS-01, por exemplo)
  	request_body {
  		max_size 12MB
  	}
  	reverse_proxy salao-em-dia-web:80 {
  		transport http {
  			read_timeout 180s
  			write_timeout 180s
  		}
  	}
  }
  ```

  A rede precisa existir antes (`docker network create NOME`, ou a rede que o proxy já usa)
  e o contêiner do proxy precisa estar nela. Nessa variação o site não publica porta, e o
  Caddy do projeto confia nos `X-Forwarded-*` vindos da rede privada, para o freio de login
  continuar vendo o endereço real de cada usuário.

- **API e site em domínios diferentes:** defina `URL_PUBLICA` e `CORS_ORIGENS` no `.env`
  e gere o site com `EXPO_PUBLIC_API_URL` apontando para a API.
- **PostgreSQL gerenciado** (RDS, Cloud SQL, Supabase): numa cópia do `docker-compose.yml`,
  apague o serviço `db`, o volume `dados_postgres` e os `depends_on: db`, e troque o
  `DATABASE_URL` do bloco `x-ambiente-da-api` pelo endereço do provedor (com
  `?sslmode=require` se ele exigir). O backup passa a ser o do provedor.
- **Imagens no S3:** `STORAGE_DRIVER=s3` e as variáveis `STORAGE_*` (bucket **privado**).

## 12. Trocar o modelo da simulação (Nano Banana)

A simulação pode seguir dois caminhos, escolhidos só por variável de ambiente
(`AI_ESTRATEGIA`). Pesquisa, preços e fontes em `docs/NANO_BANANA.md`.

| Caminho | Variáveis | Modelos |
|---|---|---|
| **especializado** (original) | `AI_ESTRATEGIA=especializado`, `AI_MODELO_TEXTO=black-forest-labs/flux-kontext-pro` | `change-haircut` para os exemplos da tela, `flux-kontext-pro` para a descrição livre |
| **instrucao** (Nano Banana) | `AI_ESTRATEGIA=instrucao`, `AI_MODELO_TEXTO=google/nano-banana-2.1`, `AI_RESOLUCAO=1K` | `google/nano-banana-2.1` para todos os pedidos |

**O termo do cliente acompanha o modelo.** O termo 1.2 diz que a foto passa pela
Replicate e pelo Google; ele é publicado pela migration `a9e4c2b7d158`, e o serviço
`migrar` aplica as migrations a cada subida. Por isso a versão com o Nano Banana e as
variáveis novas sobem **juntas**:

```bash
./scripts/backup_producao.sh /caminho/seguro/backups   # 1. backup
git pull                                                # 2. código com o Nano Banana
# 3. no .env:  AI_ESTRATEGIA=instrucao
#              AI_MODELO_TEXTO=google/nano-banana-2.1
#              AI_RESOLUCAO=1K
docker compose up -d --build --wait                     # 4. publica o termo 1.2 e liga o modelo
docker compose exec api python -m app.diagnostico_ia    # 5. confere o schema, sem custo
docker compose logs api | grep "TERMO E MODELO"         # 6. não deve aparecer nada
```

O que muda para quem usa:

- todo cliente que aceitou o termo 1.1 (ou anterior) aparece como "Aceito em versão
  anterior" e precisa ler o 1.2 e decidir de novo antes da próxima foto;
- todo profissional precisa reconhecer de novo as responsabilidades (o aviso também foi
  para a 1.2);
- o site mostra os textos novos de privacidade na hora; no Android, só com um APK novo.

Se a API subir com o modelo de um lado e o termo do outro (o Nano Banana ligado sem o
termo 1.2, ou o Kontext com o 1.2 vigente), ela registra no log uma linha
`TERMO E MODELO NÃO BATEM` dizendo o que fazer.

**Migrations de 2026-11-07** (aplicadas sozinhas na subida, pelo serviço `migrar`):

- `b5c8e1d3a742`: coluna opcional `simulacoes.curvatura` (o "cabelo natural" informado na
  etapa "Estilo e cor"). Só acrescenta; os registros existentes ficam vazios;
- `c8f2a6d4e913`: termo 1.2.1 (cliente e profissional), a 1.2 sem travessões. Quem aceitou a
  1.2 **não** precisa decidir de novo (revisão só de redação); quem aceitou a 1.1 ou antes
  continua precisando.

**Migration de 2026-11-10** (aplicada sozinha na subida, pelo serviço `migrar`):

- `c7d3f9a1e64b`: coluna opcional `simulacoes.textura` (o tipo de cabelo **desejado** na
  etapa "Estilo e cor"). Só acrescenta; os registros existentes ficam vazios ("manter o
  tipo atual"). A coluna `curvatura` fica como está e deixa de ser preenchida. O APK antigo
  continua funcionando (o campo que ele manda é ignorado e a textura da foto é mantida);
  a tela nova no Android exige um APK novo.

**Voltar ao caminho original** é trocar as duas variáveis de volta
(`AI_ESTRATEGIA=especializado` e `AI_MODELO_TEXTO=black-forest-labs/flux-kontext-pro`) e
rodar `docker compose up -d`. O termo 1.2, porém, continua dizendo que a foto vai ao
Google: antes de voltar, publique uma versão nova do termo que descreva o caminho em uso,
numa migration no mesmo padrão da `a9e4c2b7d158`. Não use `alembic downgrade` para isso:
ele se recusa a remover um termo que algum cliente já aceitou, e os consentimentos dados
sobre o 1.2 precisam continuar ligados ao texto que o cliente leu.
