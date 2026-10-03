<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
    <%@ taglib prefix="c" uri="jakarta.tags.core" %>
        <%@ taglib prefix="fmt" uri="jakarta.tags.fmt" %>
            <c:set var="ctx" value="${pageContext.request.contextPath}" />
            <fmt:setLocale value="pt_BR" />
            <!DOCTYPE html>
            <html lang="pt-BR">

            <head>
                <%@ include file="/WEB-INF/views/fragments/head.jspf" %>
                    <title>Catálogo | Vinheria Agnello</title>
            </head>

            <body>

                <header class="topo">
                    <a href="${ctx}/home" class="topo-marca">Vinheria Agnello</a>
                    <div class="topo-usuario">
                        <span>Olá,
                            <c:out value="${sessionScope.usuarioLogado.nome}" />
                        </span>
                        <form method="post" action="${ctx}/logout">
                            <button type="submit" class="botao botao-discreto">Sair</button>
                        </form>
                    </div>
                </header>

                <main class="catalogo">
                    <div class="catalogo-cabecalho">
                        <h1>Nossa adega</h1>
                        <p>${vinhos.size()} rótulos selecionados, do dia a dia às ocasiões especiais.</p>
                    </div>

                    <c:choose>
                        <c:when test="${empty vinhos}">
                            <p class="catalogo-vazio">Nenhum vinho disponível no momento. Volte em breve para conhecer
                                os novos rótulos.</p>
                        </c:when>
                        <c:otherwise>
                            <div class="grade">
                                <c:forEach var="vinho" items="${vinhos}">

                                    <%-- Novo tipo: abre um titulo de secao (lista ja vem ordenada por tipo) --%>
                                        <c:if test="${vinho.tipo != tipoAtual}">
                                            <h2 class="grade-titulo">${vinho.tipo.nome}</h2>
                                            <c:set var="tipoAtual" value="${vinho.tipo}" />
                                        </c:if>

                                        <article class="vinho ${vinho.esgotado ? 'vinho-esgotado' : ''}">
                                            <div class="vinho-imagem">
                                                <img src="${ctx}/${vinho.imagemUrl}"
                                                    alt="Garrafa de <c:out value='${vinho.nome}' />" loading="lazy"
                                                    onerror="this.remove()">
                                                <c:if test="${vinho.esgotado}">
                                                    <span class="selo-esgotado">Esgotado</span>
                                                </c:if>
                                            </div>

                                            <div class="vinho-corpo">
                                                <h3 class="vinho-nome">
                                                    <c:out value="${vinho.nome}" />
                                                </h3>
                                                <p class="vinho-origem">
                                                    <c:out value="${vinho.pais}" />
                                                    <c:if test="${not empty vinho.regiao}">,
                                                        <c:out value="${vinho.regiao}" />
                                                    </c:if>
                                                </p>
                                                <p class="vinho-uva">
                                                    <c:out value="${vinho.uva}" />
                                                </p>
                                                <p class="vinho-caracteristicas">
                                                    <c:out value="${vinho.caracteristicas}" />
                                                </p>

                                                <dl class="vinho-ficha">
                                                    <div>
                                                        <dt>Safra</dt>
                                                        <dd>
                                                            <c:choose>
                                                                <c:when test="${empty vinho.safra}">Sem safra</c:when>
                                                                <c:otherwise>${vinho.safra}</c:otherwise>
                                                            </c:choose>
                                                        </dd>
                                                    </div>
                                                    <div>
                                                        <dt>Teor</dt>
                                                        <dd>
                                                            <fmt:formatNumber value="${vinho.teorAlcoolico}"
                                                                minFractionDigits="1" maxFractionDigits="1" />%
                                                        </dd>
                                                    </div>
                                                    <div>
                                                        <dt>Volume</dt>
                                                        <dd>${vinho.volumeMl} ml</dd>
                                                    </div>
                                                </dl>

                                                <p class="vinho-preco">
                                                    <fmt:formatNumber value="${vinho.preco}" type="currency" />
                                                </p>
                                            </div>
                                        </article>

                                </c:forEach>
                            </div>
                        </c:otherwise>
                    </c:choose>
                </main>

            </body>

            </html>