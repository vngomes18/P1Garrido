# Relatório das Features do P1 — Cardápio Digital

## Feature 1 — Busca e filtro na listagem de pratos

Para a busca, usei o nome do prato, porque é assim que alguém procura no cardápio: digita "burger" e quer ver os hambúrgueres. Para o filtro, usei a categoria, que é como um cardápio de verdade se divide (entradas, pratos principais, bebidas e assim por diante). Só que o meu model `Prato` não tinha esse campo, então precisei criar. Deixei as categorias como opções fixas (Entrada, Prato principal, Acompanhamento, Bebida e Sobremesa), e não como texto livre, porque senão um cadastraria "Bebida", outro "bebidas", e o filtro deixaria itens de fora. Também juntei a busca e o filtro numa consulta só, usando `Q()`.

## Feature 2 — Validação do preço

A regra é que o preço do prato tem que ser maior que zero. Escolhi essa porque o preço do prato vai para a comanda e é com ele que a conta é fechada. Se alguém esquecesse de preencher ou digitasse errado e o prato ficasse com R$ 0,00, ele sairia de graça sem ninguém perceber. Com um preço negativo seria pior: ele descontaria do valor dos outros itens e a conta fecharia com um total menor do que o cliente realmente consumiu.

Levei a mesma ideia para o combo, e ali a regra foi um pouco além. Quem pede um combo (hambúrguer, batata e refrigerante, por exemplo) espera pagar menos do que pedindo cada item separado; se não for assim, o combo não tem motivo para existir. Por isso o preço do combo, além de ser maior que zero, precisa ter de 10% a 15% de desconto sobre a soma dos pratos que fazem parte dele, e nunca pode ficar mais caro que esses pratos separados. No combo de exemplo, os três pratos somam R$ 51,40, então o combo só pode custar entre R$ 43,69 e R$ 46,26 (ele custa R$ 45,00). Sem essa regra, daria para cadastrar um combo mais caro que os itens avulsos, e o cliente sairia no prejuízo sem perceber.

## Onde está no código

| Feature | Arquivo | Commit |
|---|---|---|
| Busca e filtro | `cardapio/views.py` (`PratoListView`) e `cardapio/templates/cardapio/prato_list.html` | `02b1a4d` |
| Preço do prato > 0 | `cardapio/forms.py` (`PratoForm.clean_preco`) | `60c9b07` |
| Preço e desconto do combo | `cardapio/forms.py` (`ComboForm.clean_preco` e `ComboForm.clean`) | `d280f47` |

Os testes das duas features estão em `cardapio/tests.py` e rodam com `python manage.py test cardapio`.
