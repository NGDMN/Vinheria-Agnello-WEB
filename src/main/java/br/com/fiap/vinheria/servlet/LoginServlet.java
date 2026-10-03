package br.com.fiap.vinheria.servlet;

import java.io.IOException;
import java.sql.SQLException;
import java.util.Optional;

import br.com.fiap.vinheria.model.Usuario;
import br.com.fiap.vinheria.service.UsuarioService;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

@WebServlet("/login")
public class LoginServlet extends HttpServlet {

    public static final String ATRIBUTO_USUARIO = "usuarioLogado";
    private static final String VIEW = "/WEB-INF/views/login.jsp";

    private final UsuarioService usuarioService = new UsuarioService();

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        HttpSession sessao = req.getSession(false);
        if (sessao != null && sessao.getAttribute(ATRIBUTO_USUARIO) != null) {
            resp.sendRedirect(req.getContextPath() + "/home");
            return;
        }
        req.getRequestDispatcher(VIEW).forward(req, resp);
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String email = req.getParameter("email");
        String senha = req.getParameter("senha");

        try {
            Optional<Usuario> usuario = usuarioService.autenticar(email, senha);

            if (usuario.isEmpty()) {
                req.setAttribute("erro", "E-mail ou senha inválidos.");
                req.setAttribute("email", email);
                req.getRequestDispatcher(VIEW).forward(req, resp);
                return;
            }

            // Nova sessao apos login (evita reaproveitamento de sessao anterior)
            HttpSession sessaoAntiga = req.getSession(false);
            if (sessaoAntiga != null) {
                sessaoAntiga.invalidate();
            }
            HttpSession sessao = req.getSession(true);
            sessao.setAttribute(ATRIBUTO_USUARIO, usuario.get());

            resp.sendRedirect(req.getContextPath() + "/home");
        } catch (SQLException e) {
            throw new ServletException("Erro ao autenticar usuário", e);
        }
    }
}
