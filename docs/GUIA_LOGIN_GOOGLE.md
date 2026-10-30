# Guia: ligar o "Entrar com Google"

O código do login com Google está pronto no servidor e no aplicativo. Para ele funcionar
com contas Google de verdade, falta um passo que só o dono do projeto pode fazer: criar as
credenciais OAuth no Google Cloud, com a conta Google dele. Este guia descreve esse passo.

Nada aqui pede senha, chave privada ou "client secret". Os **IDs de cliente** que o Google
gera são públicos por natureza (aparecem na própria tela de login do Google) e são tudo o
que o projeto precisa.

## 1. O que já está implementado

| Parte | Situação |
|---|---|
| Servidor: conferência do ID token com a biblioteca oficial `google-auth` (assinatura, validade, emissor, público, e-mail confirmado, `nonce`) | Implementado e testado (26 testes em `backend/tests/test_google.py`) |
| Servidor: conta nova no primeiro acesso, sem senha, ligada ao `sub` do Google | Implementado e testado |
| Servidor: recusa de vínculo automático por e-mail igual | Implementado e testado |
| Servidor: conectar e desconectar o Google no Perfil, exclusão de conta sem senha confirmada pelo Google | Implementado e testado |
| Banco: tabela `identidades_externas`, com restrições únicas | Migration `e5a9c3f17b20`, aplicada e revertida em teste |
| Aplicativo: botões no login, no cadastro, no Perfil e na exclusão de conta | Implementado; no navegador, o pedido ao Google e a recusa de token falso foram verificados (`espelho/e2e/google.mjs`) |
| Login com uma conta Google real | **Depende das credenciais abaixo.** Não foi testado com conta real |
| Login no Android e no iOS | **Depende das credenciais e de um build de desenvolvimento.** Não funciona no Expo Go e não foi testado em aparelho |

Sem as variáveis configuradas, o botão do Google simplesmente não aparece e o restante do
aplicativo funciona como antes (e-mail e senha).

## 2. Criar as credenciais no Google Cloud

1. Acesse <https://console.cloud.google.com/> com a sua conta Google e crie um projeto
   (por exemplo, "Salão em Dia TCC").
2. No menu, abra **Google Auth Platform** (em versões anteriores do console, "Tela de
   consentimento OAuth").
   - **Branding**: nome do app, e-mail de suporte e e-mail de contato do desenvolvedor.
   - **Audience** (público): escolha **External**. Enquanto o app estiver em modo de
     teste, só entram as contas cadastradas em **Test users**: adicione o seu e-mail e o
     de quem for testar ou avaliar.
   - **Data access** (escopos): os escopos `openid`, `email` e `profile` bastam. Eles não
     exigem verificação do Google.
3. Em **Clients**, crie um cliente do tipo **Web application**:
   - **Authorized JavaScript origins**: `http://localhost:8081`
   - **Authorized redirect URIs**: `http://localhost:8081`
   - Se publicar a versão web em outro endereço, acrescente esse endereço nos dois campos.
   - Copie o **Client ID** (termina em `.apps.googleusercontent.com`). Não é preciso
     copiar nem guardar o "client secret": o projeto não usa.
4. (Opcional, só para celular com build próprio) crie também:
   - um cliente **Android**, com o nome do pacote `com.nicolascorneli.espelho` e a
     impressão digital SHA-1 do certificado que assina o build. Nas configurações
     avançadas desse cliente, habilite **Custom URI scheme**: o aplicativo recebe a
     resposta em `com.nicolascorneli.espelho:/oauthredirect`;
   - um cliente **iOS**, com o Bundle ID `com.nicolascorneli.espelho`.

## 3. Preencher as variáveis

No servidor, `backend/.env`:

```
GOOGLE_CLIENT_IDS=SEU_ID_WEB.apps.googleusercontent.com
```

Com clientes Android e iOS, liste todos, separados por vírgula. O servidor só aceita
tokens emitidos para um desses IDs.

No aplicativo, crie `espelho/.env` a partir de `espelho/.env.example`:

```
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=SEU_ID_WEB.apps.googleusercontent.com
EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID=
EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID=
```

Reinicie a API e o Expo (`npx expo start --web --clear`): variáveis `EXPO_PUBLIC_*` são
lidas na hora de montar o pacote.

Para conferir: `GET http://localhost:8000/api/v1/auth/provedores` deve responder
`{"google": true}`, e a tela de login passa a mostrar **Entrar com Google**.

## 4. Como o login funciona

1. O aplicativo abre a tela do próprio Google. A senha do Google nunca passa pelo
   aplicativo nem pelo servidor.
2. O Google devolve um **ID token** (um JWT assinado pelo Google).
3. O aplicativo envia o token a `POST /api/v1/auth/google`.
4. O servidor confere o token com a biblioteca `google-auth`: assinatura com as chaves
   públicas do Google, validade, emissor `accounts.google.com`, público igual a um dos IDs
   configurados e e-mail confirmado pelo Google. Também confere o `nonce` do pedido.
5. A conta é encontrada pelo identificador estável do Google (`sub`), nunca pelo e-mail.

## 5. Contas que já existem com o mesmo e-mail

O servidor **não liga contas automaticamente só porque o e-mail coincide**. O cadastro por
e-mail e senha não confirma o e-mail; ligar pelo e-mail permitiria que alguém criasse uma
conta com o e-mail de outra pessoa e depois tivesse acesso aos dados dela (ou o contrário).

Quem já tem conta com senha e quer usar o Google:

1. entra com e-mail e senha;
2. vai em **Perfil → Conta Google → Conectar conta Google**.

Estar autenticado prova que a conta é sua; o token prova que a conta Google também é.
Daí em diante, os dois jeitos de entrar levam à mesma conta.

Uma conta criada pelo Google não tem senha. Por isso:

- o login por senha nunca entra nela;
- desconectar o Google é recusado (a conta ficaria sem forma de entrar);
- a exclusão da conta é confirmada entrando de novo com a mesma conta Google.

## 6. Limitações conhecidas

- **Expo Go**: não suporta este login, porque o Google precisa devolver a resposta para o
  identificador próprio do aplicativo, que o Expo Go não tem. No Expo Go o botão não
  aparece. No celular, é preciso um build de desenvolvimento (`npx expo run:android`) ou
  um build do EAS.
- **Biblioteca**: o aplicativo usa o provedor Google do `expo-auth-session`, que a
  documentação do Expo marca como "deprecated" em favor do login nativo
  (`@react-native-google-signin/google-signin`). Ele continua funcionando no SDK 57 e é o
  único caminho que também funciona no navegador sem código nativo. A troca pelo login
  nativo é a evolução indicada para uma versão publicada nas lojas.
- **Modo de teste do Google**: enquanto o app estiver em "Testing" no Google Cloud, só os
  e-mails cadastrados em "Test users" conseguem entrar.
