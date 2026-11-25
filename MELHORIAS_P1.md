# Melhorias da P1

Revisão do código da P1 antes de evoluir para a P2 (tarefa da Aula 13). A API e as telas novas herdam
o que o model já faz, então cada fragilidade abaixo foi tratada **no model/validator**, e não só no formulário.

| # | Problema na P1 | Risco | Como ficou na P2 | Situação |
|---|----------------|-------|------------------|----------|
| 1 | `abrir_comanda` era um link (GET) que criava dados; `fechar_comanda` e `remover_item` também aceitavam GET | Uma imagem ou link em outra página poderia abrir/fechar comandas (sem token CSRF) | As três views só aceitam `POST` (`@require_POST`) e os templates usam formulário com `{% csrf_token %}` | Corrigido |
| 2 | As regras de preço (`> 0` e desconto do combo) existiam só nos formulários | O Django Admin e qualquer outro caminho (a futura API) gravavam preço inválido | Regras em `cardapio/validators.py`, usadas pelo model, pelo formulário, pelo Admin e pelos serializers (um lugar só) | Corrigido |
| 3 | `ItemComanda.quantidade` aceitava `0` (`PositiveIntegerField` inclui o zero) | Item "fantasma" na comanda, com subtotal zerado | `MinValueValidator(1)` no model, valendo em formulário, Admin e API | Corrigido |
| 4 | `ItemComanda.save()` usava `if not self.preco_unitario` | Um preço unitário `0` seria sobrescrito silenciosamente pelo preço atual do prato | Troca por `is None` | Corrigido |
| 5 | Textos da interface, mensagens e erros sem acentuação ("Nao e possivel excluir", "Preco") | Aparência pouco profissional | Mantido igual à P1 para não misturar mudanças com o escopo da P2 | **Pendente** |

> Itens 1 a 4 têm testes automáticos em `cardapio/tests.py`, `cardapio/test_isolamento.py` e `cardapio/test_api.py`.
