<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
    <%@ taglib prefix="c" uri="jakarta.tags.core" %>
        <c:set var="ctx" value="${pageContext.request.contextPath}" />
        <!DOCTYPE html>
        <html lang="pt-BR">

        <head>
            <%@ include file="/WEB-INF/views/fragments/head.jspf" %>
                <title>Entrar | Vinheria Agnello</title>
        </head>

        <body class="pagina-acesso">

            <main class="acesso">
                <section class="acesso-marca">
                    <p class="marca-nome">Vinheria<br>Agnello</p>
                    <p class="marca-texto">Os rótulos da nossa loja, agora a um clique de distância.</p>
                </section>

                <section class="acesso-formulario">
                    <h1>Entrar</h1>

                    <c:if test="${param.cadastro == 'ok'}">
                        <p class="aviso aviso-sucesso" role="status">Conta criada. Entre com seu e-mail e senha.</p>
                    </c:if>

                    <c:if test="${not empty erro}">
                        <p class="aviso aviso-erro" role="alert">
                            <c:out value="${erro}" />
                        </p>
                    </c:if>

                    <form method="post" action="${ctx}/login" class="formulario" novalidate>
                        <label for="email">E-mail</label>
                        <input type="email" id="email" name="email" value="<c:out value='${email}' />"
                            autocomplete="email" required>

                        <label for="senha">Senha</label>
                        <input type="password" id="senha" name="senha" autocomplete="current-password" required>

                        <button type="submit" class="botao botao-primario">Entrar</button>
                    </form>

                    <p class="troca-acesso">Ainda não tem conta? <a href="${ctx}/signup">Criar conta</a></p>
                </section>
            </main>

        </body>

        </html>