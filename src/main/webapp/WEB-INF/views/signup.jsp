<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
    <%@ taglib prefix="c" uri="jakarta.tags.core" %>
        <c:set var="ctx" value="${pageContext.request.contextPath}" />
        <!DOCTYPE html>
        <html lang="pt-BR">

        <head>
            <%@ include file="/WEB-INF/views/fragments/head.jspf" %>
                <title>Criar conta | Vinheria Agnello</title>
        </head>

        <body class="pagina-acesso">

            <main class="acesso">
                <section class="acesso-marca">
                    <p class="marca-nome">Vinheria<br>Agnello</p>
                    <p class="marca-texto">Crie sua conta para conhecer o catálogo completo da loja.</p>
                </section>

                <section class="acesso-formulario">
                    <h1>Criar conta</h1>

                    <c:if test="${not empty erro}">
                        <p class="aviso aviso-erro" role="alert">
                            <c:out value="${erro}" />
                        </p>
                    </c:if>

                    <form method="post" action="${ctx}/signup" class="formulario" novalidate>
                        <label for="nome">Nome completo</label>
                        <input type="text" id="nome" name="nome" value="<c:out value='${nome}' />" autocomplete="name"
                            required>

                        <label for="email">E-mail</label>
                        <input type="email" id="email" name="email" value="<c:out value='${email}' />"
                            autocomplete="email" required>

                        <label for="dataNascimento">Data de nascimento</label>
                        <input type="date" id="dataNascimento" name="dataNascimento"
                            value="<c:out value='${dataNascimento}' />" aria-describedby="dica-idade" required>
                        <p id="dica-idade" class="dica">A venda de bebidas alcoólicas é permitida apenas para maiores de
                            18 anos.</p>

                        <label for="senha">Senha</label>
                        <input type="password" id="senha" name="senha" minlength="8" autocomplete="new-password"
                            aria-describedby="dica-senha" required>
                        <p id="dica-senha" class="dica">Mínimo de 8 caracteres.</p>

                        <label for="confirmacaoSenha">Confirme a senha</label>
                        <input type="password" id="confirmacaoSenha" name="confirmacaoSenha" minlength="8"
                            autocomplete="new-password" required>

                        <button type="submit" class="botao botao-primario">Criar conta</button>
                    </form>

                    <p class="troca-acesso">Já tem conta? <a href="${ctx}/login">Entrar</a></p>
                </section>
            </main>

        </body>

        </html>