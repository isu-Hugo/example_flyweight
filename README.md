# Flyweight — Demonstração com pygame

Demo ao vivo do padrão de projeto **Flyweight** (GoF): reutilizar o estado
comum entre milhares de objetos para consumir menos memória.

O cenário é uma floresta de `N` árvores. Existem apenas **5 tipos de árvore**
(no estado real: espécie, cor e textura). Cada árvore, porém, tem sua própria
posição — e é aí que o padrão entra.

---

## 1. O padrão em 30 segundos

| Papel no Flyweight | Classe aqui | O que guarda |
|---|---|---|
| **Flyweight** (estado intrínseco — compartilhado) | `TreeType` | nome, cor, `Surface` da textura |
| **Contexto** (estado extrínseco — próprio de cada objeto) | `Tree` | `x`, `y` + referência ao `TreeType` |
| **Fábrica** (garante um único flyweight por estado intrínseco) | `TreeFactory` | o *pool* (`dict`) de `TreeType` |

- **Intrínseco**: não depende do contexto do objeto — pode ser compartilhado.
- **Extrínseco**: depende da posição/história — passado por quem usa o objeto
  (aqui, aplicado em `draw(screen, cam_x, cam_y)`).

Sem o padrão, cada árvore teria sua **própria** cópia da cor, do nome e da
`Surface` inteira (`naive.py`). É esse desperdício que a demo mede.

---

## 2. Como rodar

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt

venv/bin/python main.py                       # 10.000 árvores (interativo)
venv/bin/python main.py --trees 50000         # mais árvores
venv/bin/python main.py --mode naive          # começa no modo sem Flyweight
venv/bin/python main.py --duration 15         # fecha sozinho (teste/extração)
```

**Controles:** `F` troca o modo (Flyweight ↔ Naive) · setas/`WASD`/mouse
arrastado/roda do mouse movem a câmera · `ESC` sai.

---

## 3. O que o HUD mostra

```
Modo: FLYWEIGHT (padrao Flyweight)
Arvores (contextos): 50,000          <- objetos com estado próprio
TreeTypes (flyweights): 5            <- flyweights realmente criados
Objetos de dominio: 50,005           <- 50.000 contextos + 5 flyweights
Texturas compartilhadas: 5 -> 0.0 MB <- 5 surfaces vs 50.000 no modo naive

Memoria Python (tracemalloc): ... MB <- heap do Python (árvore, listas, etc.)
RSS atual (coluna do btop): ... MB   <- é O MESMO número que o btop mostra
RSS pico do processo: ... MB
FPS: 60
```

- **`tracemalloc`**: módulo da stdlib que mede o heap do Python. Mostra o custo
  dos objetos de domínio (árvores, listas, dicionários).
- **`RSS` lido de `/proc/self/status` (`VmRSS`/`VmHWM`)**: memória residente do
  processo — exatamente a coluna **MEM** que você vê no **btop**.
- **Memória de texturas**: estimativa `nº de surfaces × 18 × 24 × 4 bytes`.
  No modo Flyweight são 5 surfaces; no Naive, uma por árvore. Como as
  `Surface` são alocadas pelo SDL (fora do heap do Python), esse custo aparece
  no RSS, não no `tracemalloc` — por isso o HUD mostra as duas métricas.

---

## 4. Comparando com o btop (recomendado para a apresentação)

Abra **dois terminais** e deixe o `btop` numa terceira janela:

```bash
# terminal 1                              # terminal 2
venv/bin/python main.py --mode flyweight --trees 50000
venv/bin/python main.py --mode naive     --trees 50000
```

Observe a coluna MEM de cada processo no btop: o processo `naive` usa bem mais
(memória de texturas + mais tempo de plantio).

> **Cuidado importante (e ótimo assunto para perguntarem):** dentro de um
> processo só, o RSS **não cai** quando você volta do modo Naive para o
> Flyweight com `F`. O alocador do sistema guarda as páginas livres para
> reuso — liberar para o SO só acontece sob pressão de memória. Por isso a
> comparação honesta é **processo a processo** (dois terminais) ou pelo
> `compare.py`. O que cai imediatamente ao trocar com `F` é o número do
> `tracemalloc` e o contador de surfaces do HUD.

### Tabela automática

```bash
venv/bin/python compare.py --trees 10000 50000 100000 --out resultados.md
```

Cada caso roda em processo separado (RSS honesto) e imprime markdown pronto
para colar nos slides. Resultados medidos nesta máquina (10k/50k/100k):

| Árvores | Modo | Texturas | Mem. texturas | Heap Python | RSS (btop) | Plantio | FPS |
|---:|---|---:|---:|---:|---:|---:|---:|
| 10,000 | flyweight | 5 | 0.0 MB | 1.2 MB | 118.2 MB | 0.09s | 62 |
| 10,000 | naive | 10,000 | 16.5 MB | 2.1 MB | 137.2 MB | 0.92s | 62 |
| 50,000 | flyweight | 5 | 0.0 MB | 6.0 MB | 133.1 MB | 0.44s | 57 |
| 50,000 | naive | 50,000 | 82.4 MB | 9.9 MB | 239.4 MB | 4.47s | 51 |
| 100,000 | flyweight | 5 | 0.0 MB | 11.9 MB | 154.5 MB | 0.88s | 29 |
| 100,000 | naive | 100,000 | 164.8 MB | 19.6 MB | 367.0 MB | 8.85s | 27 |

Leitura para os slides: com 100 mil árvores, o modo Naive gasta **+212 MB de
RSS**, **+165 MB só de texturas duplicadas** e demora **10× mais** para
plantar — e renderiza exatamente a mesma imagem.

---

## 5. Explicação do código

```
main.py                  CLI: argumentos, janela, resumo/métricas (--json)
compare.py               roda cada caso em subprocesso e gera tabela markdown
flyweight_forest/
├── textures.py          geração procedural dos sprites + TREE_SPECS (5 tipos)
├── flyweight.py         TreeType, Tree, TreeFactory, Forest   <- O PADRÃO
├── naive.py             NaiveTree, NaiveForest                <- contra-exemplo
└── app.py               janela pygame, toggle, HUD, métricas de memória
```

### `flyweight.py` — o padrão

```python
@dataclass(frozen=True)
class TreeType:                      # FLYWEIGHT — imutável e compartilhado
    name: str
    color: tuple[int, int, int]
    surface: pygame.Surface          # estado intrínseco pesado

    def draw(self, screen, x, y):
        screen.blit(self.surface, self.surface.get_rect(center=(x, y)))
```

`frozen=True` é intencional: um flyweight não pode ter estado extrínseco
escondido — se alguém tentasse alterar, daria erro.

```python
class TreeFactory:
    def __init__(self):
        self._pool: dict[tuple, TreeType] = {}
        self.types_created = 0       # prova didática de que só 5 existem

    def get_type(self, name, color, seed):
        key = (name, color, seed)
        tree_type = self._pool.get(key)
        if tree_type is None:        # miss: cria UMA vez e guarda
            surface = make_tree_surface(color, seed).convert_alpha()
            tree_type = TreeType(name, color, surface)
            self._pool[key] = tree_type
            self.types_created += 1
        return tree_type             # hit: devolve o já existente
```

```python
class Tree:                          # CONTEXTO — só estado extrínseco
    __slots__ = ("x", "y", "tree_type")   # remove o dict de instância: -40%

    def __init__(self, x, y, tree_type):
        ...
    def draw(self, screen, cam_x, cam_y):
        # a posição (extrínseco) é passada aqui, em tempo de uso
        self.tree_type.draw(screen, self.x - cam_x, self.y - cam_y)
```

Plantio (`Forest.plant`): para cada árvore, a fábrica devolve o mesmo
`TreeType` — 50.000 `Tree` apontando para 5 `TreeType`.

### `naive.py` — o contra-exemplo

```python
class NaiveTree:
    def __init__(self, x, y, name, color, seed):
        self.name = name                          # copiado N vezes
        self.color = color                        # copiado N vezes
        self.surface = make_tree_surface(color, seed)  # Surface NOVA N vezes
```

Mesmo resultado visual, só que com N `Surface` idênticas em memória. Em
`textures.make_tree_surface(color, seed)` a aparência é função apenas de
`(color, seed)` — ou seja, o estado intrínseco **é** compartilhável por
construção; o Naive é que insiste em duplicá-lo.

### `app.py` — a demonstração

- `_build_forest()`: `gc.collect()` → mede `tracemalloc` e RSS **antes/depois**
  do plantio → guarda tempo, nº de surfaces e MB de texturas. Chamado na
  inicialização e a cada toggle (`F`), garantindo que só a floresta do modo
  ativo exista em memória.
- `rss_mb()` / `rss_peak_mb()`: leem `VmRSS` e `VmHWM` de
  `/proc/self/status` (não use `resource.ru_maxrss` aqui — nesse ambiente ele
  vem herdado/corrompido do processo pai).
- Loop de render: varre as árvores, desenha só as que estão na janela, HUD
  por cima.

---

## 6. Roteiro sugerido para o seminário

1. **Abertura (2 min):** o problema — "100.000 objetos, mas só 5 configurações
   distintas. Cada um guardando uma cópia dos dados iguais é desperdício."
2. **Conceito (3 min):** intrínseco × extrínseco; fábrica com pool; UML mental
   (Flyweight / Context / FlyweightFactory).
3. **Código (4 min):** mostrar `TreeType` + `TreeFactory.get_type` (o `dict` é
   o coração) e o contraste com `naive.NaiveTree`.
4. **Demo ao vivo (5 min):**
   - `venv/bin/python main.py --trees 50000` → Flyweight: 5 texturas, plantio
     ~0,4 s, HUD e FPS;
   - tecla `F` → Naive: contadores explodem, plantio demora ~4,5 s (o público
     *vê* a pausa);
   - tecla `F` de volta e **explicar porque o RSS do btop não cai** (alocador
     reutiliza páginas) — mostra domínio do assunto.
   - Dois terminais + btop lado a lado para o número que interessa.
5. **Números (2 min):** tabela do `compare.py` — +212 MB e 10× mais lento.
6. **Encerramento (1 min):** quando usar / quando não usar (padrão só compensa
   se o estado intrínseco é grande e os objetos são muitos; complexidade extra
   e o estado extrínseco precisa ser passado de fora).

### Quantidades que funcionam bem

| Objetivo | Comando |
|---|---|
| Demo ao vivo fluida (≥60 FPS) | `--trees 10000` ou `--trees 50000` |
| Números grandes para a tabela | `--trees 100000` (plantio naive ~9 s, 27 FPS) |
| Estresse/memória máxima | `--trees 200000` (naive ≈ 544 MB, 14 FPS — evite ao vivo) |

---

## 7. Limitações honestas da medição

- `tracemalloc` **não** vê a memória das `Surface` (alocadas pelo SDL) — por
  isso o HUD tem a linha separada de "memória de texturas".
- O RSS tem um piso (pygame + SDL + janela ≈ 110 MB) — o que interessa é a
  **diferença** entre os modos, não o valor absoluto.
- No mesmo processo, o RSS só sobe (ver seção 4).
