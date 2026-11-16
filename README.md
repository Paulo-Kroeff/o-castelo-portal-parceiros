# O Castelo — Portal do Parceiro

Portal independente para agências parceiras de O Castelo, em São Roque.
Site estático em português, sem autenticação e sem dependências de build.

## Conteúdo

- Apresentação da experiência, argumentos comerciais e apoio a campanhas.
- Biblioteca com os 79 materiais do acervo oficial mapeado em 16/11/2026.
- 50 fotografias, cinco vídeos via Google Drive e 109 perguntas frequentes.
- Guia comercial em 28 páginas JPEG para folhear e ampliar no próprio portal.
- Download do PDF original mantido no Google Drive.
- Busca, filtros, favoritos e checklist salvos somente no navegador.
- Carrossel com dez fotos, intervalo de quatro segundos e controles de pausa.

## Executar localmente

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory dist
```

Abra http://127.0.0.1:4173/. A publicação usa `dist` como diretório de saída
do Vercel e não precisa de comandos de instalação ou build.

## Organização

- `dist/index.html`, `styles.css` e `app.js`: interface e navegação.
- `dist/guide.js` e `dist/assets/guia`: leitor e páginas do guia.
- `dist/data.js`: catálogo de arquivos e perguntas frequentes.
- `dist/manifest.webmanifest` e `sw.js`: recursos de PWA e cache de leitura.

## Atualização do acervo

O catálogo é uma fotografia do Drive na data do mapeamento; não existe
sincronização automática. Novos arquivos e alterações editoriais devem ser
incorporados e revisados antes da publicação. Os links dos materiais apontam
para os originais. Vídeos, Drive e Canva precisam de conexão à internet.

As imagens do portal são prévias otimizadas. As 28 páginas do guia foram
convertidas fielmente do documento fornecido. O PDF original não faz parte
do repositório: seu download continua disponível no Drive.

As páginas e imagens consultadas podem permanecer disponíveis offline após
o primeiro acesso. Favoritos e checklist são locais a cada navegador.

## Direitos dos materiais

Marca, fotografias e materiais comerciais pertencem aos respectivos titulares.
Este repositório não concede uma licença de redistribuição desses materiais.
