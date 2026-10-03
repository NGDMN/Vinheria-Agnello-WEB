package br.com.fiap.vinheria.service;

import java.sql.SQLException;
import java.util.List;

import br.com.fiap.vinheria.dao.VinhoDao;
import br.com.fiap.vinheria.model.Vinho;

public class VinhoService {

    private final VinhoDao vinhoDao = new VinhoDao();

    public List<Vinho> listarCatalogo() throws SQLException {
        return vinhoDao.listarAtivos();
    }
}
