-- ============================================================================
-- 🛡️ SESMT HUC v3.0 - Script SQL Completo de Instalação
-- Hospital Universitário do Ceará
-- Execute este script no SQL Editor do Supabase (uma vez só)
-- ============================================================================

-- 1. EXTENSÕES NECESSÁRIAS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. TABELA: CONFIGURAÇÕES
CREATE TABLE IF NOT EXISTS configuracoes (
    id SERIAL PRIMARY KEY,
    chave TEXT UNIQUE NOT NULL,
    valor TEXT,
    descricao TEXT,
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

INSERT INTO configuracoes (chave, valor, descricao) VALUES
('app_password', '1234', 'Senha padrão do sistema'),
('app_password_hash', '', 'Hash SHA-256 da senha admin'),
('url_sistema', 'https://seusistema.streamlit.app', 'URL base para links'),
('ficha_template', 'Recebi os equipamentos acima descritos, de acordo com a NR-6, e me comprometo a: (a) utilizá-los corretamente durante todo o período de exposição aos riscos; (b) conservá-los em bom estado; (c) comunicar imediatamente ao empregador qualquer alteração que os torne ineficazes; (d) cumprir as orientações de uso, guarda e higienização.', 'Termo de responsabilidade'),
('lgpd_base_legal', 'Art. 11, II, "a" da LGPD - Cumprimento de obrigação legal ou regulatória (NR-6)', 'Base legal do tratamento de dados'),
('lgpd_prazo_retencao', '5', 'Prazo de retenção de dados em anos'),
('whatsapp_provedor', 'desativado', 'Provedor WhatsApp'),
('whatsapp_callmebot_apikey', '', 'API Key do CallMeBot'),
('whatsapp_meta_token', '', 'Access Token Meta'),
('whatsapp_meta_phone_id', '', 'Phone Number ID do Meta')
ON CONFLICT (chave) DO NOTHING;

-- 3. TABELA: SETORES
CREATE TABLE IF NOT EXISTS setores (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT NOW()
);

INSERT INTO setores (nome, descricao) VALUES
('SESMT', 'Serviço Especializado em Segurança e Medicina do Trabalho'),
('UTI', 'Unidade de Terapia Intensiva'),
('EMERGÊNCIA', 'Pronto Atendimento / Emergência'),
('CENTRO CIRÚRGICO', 'Bloco Cirúrgico'),
('FARMÁCIA', 'Farmácia Hospitalar'),
('RADIOLOGIA', 'Imagem e Diagnóstico'),
('LABORATÓRIO', 'Análises Clínicas'),
('ADMINISTRATIVO', 'Setor Administrativo'),
('MANUTENÇÃO', 'Engenharia e Manutenção'),
('LIMPEZA', 'Higienização Hospitalar'),
('NUTRIÇÃO', 'Nutrição e Dietética'),
('RECEPÇÃO', 'Atendimento ao Público')
ON CONFLICT (nome) DO NOTHING;

-- 4. TABELA: FUNÇÕES / CARGOS (NOVA)
CREATE TABLE IF NOT EXISTS funcoes (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    risco TEXT DEFAULT '2 - Médio',
    ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

INSERT INTO funcoes (nome, descricao, risco) VALUES
('ENFERMEIRO(A)', 'Cuidados diretos ao paciente', '3 - Grave'),
('TÉCNICO(A) DE ENFERMAGEM', 'Auxílio em cuidados ao paciente', '3 - Grave'),
('MÉDICO(A)', 'Atendimento médico', '3 - Grave'),
('FISIOTERAPEUTA', 'Reabilitação e fisioterapia', '2 - Médio'),
('FARMACÊUTICO(A)', 'Dispensação de medicamentos', '2 - Médio'),
('AUXILIAR DE FARMÁCIA', 'Apoio na farmácia', '2 - Médio'),
('TÉCNICO(A) DE RADIOLOGIA', 'Exames de imagem', '3 - Grave'),
('AUXILIAR DE LIMPEZA', 'Higienização de ambientes', '2 - Médio'),
('RECEPCIONISTA', 'Atendimento ao público', '1 - Leve'),
('AUXILIAR ADMINISTRATIVO', 'Apoio administrativo', '1 - Leve'),
('MOTORISTA', 'Transporte', '2 - Médio'),
('ELETRICISTA', 'Manutenção elétrica', '3 - Grave'),
('ENCANADOR', 'Manutenção hidráulica', '2 - Médio'),
('COZINHEIRO(A)', 'Preparo de refeições', '2 - Médio'),
('AUXILIAR DE NUTRIÇÃO', 'Apoio na cozinha', '2 - Médio'),
('SEGURANÇA', 'Vigilância hospitalar', '2 - Médio'),
('ESTAGIÁRIO(A)', 'Estágio supervisionado', '2 - Médio'),
('TERCEIRIZADO(A)', 'Prestação de serviços', '2 - Médio')
ON CONFLICT (nome) DO NOTHING;

-- 5. TABELA: COLABORADORES (oficiais)
CREATE TABLE IF NOT EXISTS oficiais (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    matricula TEXT UNIQUE NOT NULL,
    setor TEXT,
    funcao TEXT,
    whatsapp TEXT,
    vinculo TEXT DEFAULT 'ISGH',
    data_criacao TIMESTAMP DEFAULT NOW()
);

-- Adiciona colunas novas
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='oficiais' AND column_name='data_admissao') THEN
        ALTER TABLE oficiais ADD COLUMN data_admissao DATE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='oficiais' AND column_name='consentimento_lgpd') THEN
        ALTER TABLE oficiais ADD COLUMN consentimento_lgpd BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='oficiais' AND column_name='data_consentimento') THEN
        ALTER TABLE oficiais ADD COLUMN data_consentimento TIMESTAMP;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='oficiais' AND column_name='foto_url') THEN
        ALTER TABLE oficiais ADD COLUMN foto_url TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='oficiais' AND column_name='assinatura_url') THEN
        ALTER TABLE oficiais ADD COLUMN assinatura_url TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='oficiais' AND column_name='ativo') THEN
        ALTER TABLE oficiais ADD COLUMN ativo BOOLEAN DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='oficiais' AND column_name='data_atualizacao') THEN
        ALTER TABLE oficiais ADD COLUMN data_atualizacao TIMESTAMP DEFAULT NOW();
    END IF;
END $$;

-- 6. TABELA: EPI (ep)
CREATE TABLE IF NOT EXISTS ep (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    ca TEXT NOT NULL,
    validade DATE NOT NULL,
    data_criacao TIMESTAMP DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ep' AND column_name='tamanhos') THEN
        ALTER TABLE ep ADD COLUMN tamanhos TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ep' AND column_name='estoque_minimo') THEN
        ALTER TABLE ep ADD COLUMN estoque_minimo INTEGER DEFAULT 5;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ep' AND column_name='ativo') THEN
        ALTER TABLE ep ADD COLUMN ativo BOOLEAN DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ep' AND column_name='data_atualizacao') THEN
        ALTER TABLE ep ADD COLUMN data_atualizacao TIMESTAMP DEFAULT NOW();
    END IF;
END $$;

INSERT INTO ep (nome, ca, validade, tamanhos, estoque_minimo) VALUES
('LUVA NITRÍLICA PROCEDIMENTO', '42376', '2027-12-31', 'P,M,G', 50),
('LUVA NITRÍLICA QUÍMICA', '42377', '2027-12-31', 'P,M,G,GG', 30),
('MÁSCARA CIRÚRGICA TRIPLA', '42378', '2027-06-30', 'UNICO', 200),
('MÁSCARA PFF2 (N95)', '42379', '2027-06-30', 'P,M,G', 100),
('PROTETOR FACIAL (FACE SHIELD)', '42380', '2027-12-31', 'UNICO', 40),
('ÓCULOS DE PROTEÇÃO', '42381', '2027-12-31', 'UNICO', 30),
('AVENTAL IMPERMEÁVEL', '42382', '2027-12-31', 'P,M,G,GG', 20),
('AVENTAL DESCARTÁVEL', '42383', '2027-12-31', 'UNICO', 100),
('CAPOTE/CAPUZ DESCARTÁVEL', '42384', '2027-12-31', 'UNICO', 50),
('SAPATILHA/PROTECTOR DE CALÇADO', '42385', '2027-12-31', 'P,M,G,GG', 30),
('CAPACETE DE SEGURANÇA', '42386', '2027-12-31', 'UNICO', 10),
('LUVA DE COURO RASPA', '42387', '2027-12-31', 'M,G,GG', 15),
('PROTETOR AURICULAR (PLUG)', '42388', '2027-12-31', 'UNICO', 50),
('PROTETOR AURICULAR (CONCHA)', '42389', '2027-12-31', 'UNICO', 20),
('CREME PROTECTOR', '42390', '2027-12-31', 'UNICO', 20),
('JALECO', '42391', '2027-12-31', 'P,M,G,GG,EXG', 25)
ON CONFLICT DO NOTHING;

-- 7. TABELA: ENTREGAS
CREATE TABLE IF NOT EXISTS entregas (
    id SERIAL PRIMARY KEY,
    id_func INTEGER REFERENCES oficiais(id) ON DELETE RESTRICT,
    id_epi INTEGER REFERENCES ep(id) ON DELETE RESTRICT,
    token TEXT UNIQUE NOT NULL,
    quantidade INTEGER DEFAULT 1,
    status TEXT DEFAULT 'Pendente ⏳',
    data_entrega TIMESTAMP DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='entregas' AND column_name='tamanho') THEN
        ALTER TABLE entregas ADD COLUMN tamanho TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='entregas' AND column_name='observacao') THEN
        ALTER TABLE entregas ADD COLUMN observacao TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='entregas' AND column_name='data_devolucao') THEN
        ALTER TABLE entregas ADD COLUMN data_devolucao DATE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='entregas' AND column_name='usuario_registro') THEN
        ALTER TABLE entregas ADD COLUMN usuario_registro TEXT;
    END IF;
END $$;

-- 8. TABELA: AUDITORIA (LGPD)
CREATE TABLE IF NOT EXISTS auditoria (
    id SERIAL PRIMARY KEY,
    data_hora TIMESTAMP DEFAULT NOW(),
    usuario TEXT,
    acao TEXT NOT NULL,
    tabela TEXT NOT NULL,
    registro_id TEXT,
    detalhes TEXT,
    ip TEXT,
    data_criacao TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auditoria_data ON auditoria(data_hora DESC);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria(usuario);
CREATE INDEX IF NOT EXISTS idx_auditoria_acao ON auditoria(acao);
CREATE INDEX IF NOT EXISTS idx_auditoria_tabela ON auditoria(tabela);

-- 9. POLÍTICAS RLS
ALTER TABLE IF EXISTS oficiais ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ep ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS entregas ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS funcoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS auditoria ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Permitir leitura oficiais" ON oficiais FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "Permitir leitura ep" ON ep FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "Permitir leitura entregas" ON entregas FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "Permitir leitura funcoes" ON funcoes FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "Permitir leitura auditoria" ON auditoria FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Permitir escrita oficiais" ON oficiais FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Permitir escrita ep" ON ep FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Permitir escrita entregas" ON entregas FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Permitir escrita funcoes" ON funcoes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY IF NOT EXISTS "Permitir escrita auditoria" ON auditoria FOR ALL USING (true) WITH CHECK (true);

-- 10. TRIGGER: atualizar data_atualizacao
CREATE OR REPLACE FUNCTION atualizar_data_modificacao()
RETURNS TRIGGER AS $$
BEGIN
    NEW.data_atualizacao = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    DROP TRIGGER IF EXISTS trg_oficiais_atualizacao ON oficiais;
    CREATE TRIGGER trg_oficiais_atualizacao BEFORE UPDATE ON oficiais FOR EACH ROW EXECUTE FUNCTION atualizar_data_modificacao();
    
    DROP TRIGGER IF EXISTS trg_ep_atualizacao ON ep;
    CREATE TRIGGER trg_ep_atualizacao BEFORE UPDATE ON ep FOR EACH ROW EXECUTE FUNCTION atualizar_data_modificacao();
    
    DROP TRIGGER IF EXISTS trg_funcoes_atualizacao ON funcoes;
    CREATE TRIGGER trg_funcoes_atualizacao BEFORE UPDATE ON funcoes FOR EACH ROW EXECUTE FUNCTION atualizar_data_modificacao();
END $$;

-- 11. ÍNDICES DE PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_oficiais_matricula ON oficiais(matricula);
CREATE INDEX IF NOT EXISTS idx_oficiais_nome ON oficiais(nome);
CREATE INDEX IF NOT EXISTS idx_oficiais_setor ON oficiais(setor);
CREATE INDEX IF NOT EXISTS idx_oficiais_funcao ON oficiais(funcao);
CREATE INDEX IF NOT EXISTS idx_oficiais_ativo ON oficiais(ativo);

CREATE INDEX IF NOT EXISTS idx_ep_nome ON ep(nome);
CREATE INDEX IF NOT EXISTS idx_ep_ca ON ep(ca);
CREATE INDEX IF NOT EXISTS idx_ep_validade ON ep(validade);
CREATE INDEX IF NOT EXISTS idx_ep_ativo ON ep(ativo);

CREATE INDEX IF NOT EXISTS idx_entregas_id_func ON entregas(id_func);
CREATE INDEX IF NOT EXISTS idx_entregas_id_epi ON entregas(id_epi);
CREATE INDEX IF NOT EXISTS idx_entregas_token ON entregas(token);
CREATE INDEX IF NOT EXISTS idx_entregas_status ON entregas(status);
CREATE INDEX IF NOT EXISTS idx_entregas_data ON entregas(data_entrega DESC);

CREATE INDEX IF NOT EXISTS idx_funcoes_nome ON funcoes(nome);
CREATE INDEX IF NOT EXISTS idx_funcoes_ativo ON funcoes(ativo);

-- 12. VIEWS
CREATE OR REPLACE VIEW vw_resumo_entregas AS
SELECT 
    o.id AS func_id,
    o.nome AS func_nome,
    o.matricula,
    o.setor,
    o.funcao,
    COUNT(e.id) AS total_entregas,
    SUM(e.quantidade) AS total_epis,
    MAX(e.data_entrega) AS ultima_entrega
FROM oficiais o
LEFT JOIN entregas e ON o.id = e.id_func
WHERE o.ativo = TRUE
GROUP BY o.id, o.nome, o.matricula, o.setor, o.funcao;

CREATE OR REPLACE VIEW vw_alertas_ca AS
SELECT 
    id,
    nome,
    ca,
    validade,
    CASE 
        WHEN validade < CURRENT_DATE THEN 'VENCIDO'
        WHEN validade <= CURRENT_DATE + INTERVAL '60 days' THEN 'VENCENDO'
        ELSE 'OK'
    END AS situacao,
    (validade - CURRENT_DATE) AS dias_restantes
FROM ep
WHERE ativo = TRUE AND (validade < CURRENT_DATE + INTERVAL '90 days');

-- 13. COMENTÁRIOS LGPD
COMMENT ON TABLE oficiais IS 'Dados pessoais de colaboradores - Tratamento conforme LGPD Art. 11, II, a (obrigação legal NR-6)';
COMMENT ON TABLE entregas IS 'Registro de entregas de EPI - Dados sensíveis de saúde ocupacional. Acesso restrito ao SESMT.';
COMMENT ON TABLE auditoria IS 'Logs de auditoria para rastreabilidade e conformidade LGPD Art. 37 e 38.';

-- FIM
SELECT '🛡️ SESMT HUC v3.0 - Instalação concluída com sucesso!' AS status;
