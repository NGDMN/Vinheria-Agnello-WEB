package br.com.fiap.vinheria.servlet;

import java.io.IOException;
import java.sql.SQLException;

import br.com.fiap.vinheria.service.VinhoService;
import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

@WebServlet("/home")
public class HomeServlet extends HttpServlet {

    private static final String VIEW = "/WEB-INF/views/home.jsp";

    private final VinhoService vinhoService = new VinhoService();

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        try {
            req.setAttribute("vinhos", vinhoService.listarCatalogo());
            req.getRequestDispatcher(VIEW).forward(req, resp);
        } catch (SQLException e) {
            throw new ServletException("Erro ao carregar o catálogo", e);
        }
    }
}
