import asyncio
from playwright.async_api import async_playwright
import re

def produto_relevante(nome_produto, termo_pesquisado):
    nome = nome_produto.lower()
    termo = termo_pesquisado.lower()
    if not re.search(rf'\b{re.escape(termo)}\b', nome):
        return False
    palavras = nome.split()
    if termo not in palavras[:3]:
        return False
    return True

class Supermercado:
    def __init__(self, nome):
        self.nome = nome

    async def buscar(self, page, produto, quantidade, unidade):
        raise NotImplementedError("Subclasse deve implementar este método")

class PingoDoce(Supermercado):
    def __init__(self):
        super().__init__("Pingo Doce")

    async def buscar(self, page, produto, quantidade, unidade):
        url = f"https://www.pingodoce.pt/on/demandware.store/Sites-pingo-doce-Site/default/Search-Show?q={produto}"
        await page.goto(url)
        try:
            await page.wait_for_selector(".product-tile-body", timeout=8000)
        except:
            return None

        produtos_encontrados = await page.query_selector_all(".product-tile-body")
        melhores = []

        for prod in produtos_encontrados:
            nome_el = await prod.query_selector(".product-name-link a")
            preco_el = await prod.query_selector(".sales")
            unit_el = await prod.query_selector(".product-unit")

            nome = await nome_el.inner_text() if nome_el else ""
            if not produto_relevante(nome, produto):
                continue

            #nome = await nome_el.inner_text() if nome_el else ""
            preco_text = await preco_el.inner_text() if preco_el else ""
            unit_raw = await unit_el.inner_text() if unit_el else ""
            unit = unit_raw.split('|')[0].strip()

            unidade_base = unit.split()[-1].lower()
            if unidade_base != unidade.lower():
                continue

            try:
                quantidade_base = float(unit.split()[0].replace(',', '.'))
            except:
                quantidade_base = 1.0

            preco_match = re.search(r"[\d,.]+", preco_text)
            preco_valor = float(preco_match.group().replace(",", ".")) if preco_match else float("inf")

            preco_calculado = preco_valor * quantidade

            melhores.append({
                "nome": nome.strip(),
                "preco": round(preco_calculado, 2)
            })

        if melhores:
            return min(melhores, key=lambda x: x["preco"])
        return None

class Continente(Supermercado):
    def __init__(self):
        super().__init__("Continente")

    async def scroll_pagina(self, page):
            previous_height = await page.evaluate("document.body.scrollHeight")
            while True:
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == previous_height:
                    break
                previous_height = new_height

    async def buscar(self, page, produto, quantidade, unidade):
        url = f"https://www.continente.pt/pesquisa/?q={produto}"
        await page.goto(url)
        try:
            await page.wait_for_selector("div.ct-tile-body", timeout=8000)
        except:
            return None

        await self.scroll_pagina(page)
        
        produtos = await page.query_selector_all("div.ct-tile-body")
        melhores = []

        for prod in produtos:
            nome_el = await prod.query_selector("h2.pwc-tile--description")
            nome = await nome_el.inner_text() if nome_el else ""
            if not produto_relevante(nome, produto):
                continue
            #nome = await nome_el.inner_text() if nome_el else ""
            # Obter bloco de preço
            preco_valor_el = await prod.query_selector("span.value")
            preco_valor_raw = await preco_valor_el.inner_text() if preco_valor_el else ""
            preco_match = re.search(r"[\d,.]+", preco_valor_raw)
            preco_valor = float(preco_match.group().replace(",", ".")) if preco_match else float("inf")

            # Extrair texto do tipo "emb. 1 lt" (caso exista)
            unit_raw_el = await prod.query_selector("p.pwc-tile--quantity")
            unit_raw_text = await unit_raw_el.inner_text() if unit_raw_el else ""
            
            match_emb = re.search(r"emb\.\s*([\d.,]+)\s*(\w+)", unit_raw_text.lower())
            
            if match_emb:
                quantidade_base = float(match_emb.group(1).replace(",", "."))
                unidade_embalagem = match_emb.group(2).lower()
            else:
                quantidade_base = 1.0
                unidade_embalagem = unit_raw_text.split()[-1].lower() if unit_raw_text else "un"

            # Normalizar unidades
            mapa = {"lt": "l", "l": "l", "kg": "kg", "g": "g", "un": "un"}
            unidade_base = mapa.get(unidade_embalagem, unidade_embalagem)
            unidade_input = mapa.get(unidade.lower(), unidade.lower())

            if unidade_base != unidade_input:
                continue

            preco_final = (preco_valor * quantidade) / quantidade_base
            
            melhores.append({
                "nome": nome.strip(),
                "preco": round(preco_final, 2)
            })

        if melhores:
            return min(melhores, key=lambda x: x["preco"])
        return None

class Aldi(Supermercado):
    def __init__(self):
        super().__init__("Aldi")

    async def scroll_pagina(self, page):
            previous_height = await page.evaluate("document.body.scrollHeight")
            while True:
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == previous_height:
                    break
                previous_height = new_height

    async def buscar(self, page, produto, quantidade, unidade):
        url = f"https://www.aldi.pt/procurar.html?query={produto}"
        await page.goto(url)
        try:
            await page.wait_for_selector("div.mod-article-tile__info", timeout=8000)
        except:
            return None

        await self.scroll_pagina(page)
        
        produtos = await page.query_selector_all("div.mod-article-tile")
        if not produtos:
            return None

        melhores = []

        for prod in produtos:
            nome_el = await prod.query_selector("span.mod-article-tile__title")
            nome = await nome_el.inner_text() if nome_el else ""
            if not produto_relevante(nome, produto):
                continue
            #nome = await nome_el.inner_text() if nome_el else ""
            
            # Obter bloco de preço
            try:
                preco_el = await prod.query_selector("div.price span.price__wrapper") or await prod.query_selector("div.price span.price__main")
                if not preco_el:
                    continue

                preco_raw = await preco_el.text_content()
                preco_valor = float(preco_raw.replace(",", ".").strip())

            except Exception as e:
                continue  # se não encontrar, passa para o próximo produto
            
            # Extrair texto do tipo "1-l-unidade" (caso exista)
            unit_el = await prod.query_selector("span.price__unit")
            unit_raw_text = await unit_el.inner_text() if unit_el else ""

            match_emb = re.search(r"emb\.\s*([\d.,]+)\s*([a-zA-Z]+)", unit_raw_text.lower())
            if not match_emb:
                match_emb = re.search(r"([\d.,]+)\s*-\s*([a-zA-Z]+)", unit_raw_text.lower())

            if match_emb:
                quantidade_base = float(match_emb.group(1).replace(",", "."))
                unidade_embalagem = match_emb.group(2).lower()
            else:
                quantidade_base = 1.0
                unidade_embalagem = "un"

            # Normalizar unidades
            mapa = {"lt": "l", "l": "l", "kg": "kg", "g": "g", "un": "un"}
            unidade_base = mapa.get(unidade_embalagem, unidade_embalagem)
            unidade_input = mapa.get(unidade.lower(), unidade.lower())

            if unidade_base != unidade_input:
                continue

            preco_final = (preco_valor * quantidade) / quantidade_base
            
            melhores.append({
                "nome": nome.strip(),
                "preco": round(preco_final, 2)
            })

        if melhores:
            return min(melhores, key=lambda x: x["preco"])
        return None
    
class Auchan(Supermercado):
    def __init__(self):
        super().__init__("Auchan")

    async def buscar(self, page, produto, quantidade, unidade):
        url = f"https://www.auchan.pt/pt/pesquisa?search-button=&q={produto}"
        await page.goto(url)
        
        try:
            await page.wait_for_selector(".auc-product", timeout=8000)
        except:
            return None

        produtos_encontrados = await page.query_selector_all(".auc-product")
        
        melhores = []

        for prod in produtos_encontrados:
            nome_el = await prod.query_selector("div.auc-product-tile__name a")
            preco_el = await prod.query_selector("div.price span.value")
            nome = await nome_el.inner_text() if nome_el else ""
            if not produto_relevante(nome, produto):
                continue
            #nome = await nome_el.inner_text() if nome_el else ""
            preco_text = await preco_el.inner_text() if preco_el else ""
            
            match_emb = re.search(r"([\d.,]+)\s*([a-zA-Z]+)$", nome.lower().strip())
            if match_emb:
                quantidade_base = float(match_emb.group(1).replace(",", "."))
                unidade_embalagem = match_emb.group(2).lower()
            else:
                quantidade_base = 1.0
                unidade_embalagem = "un"

            # Normalizar unidades
            mapa = {"lt": "l", "l": "l", "kg": "kg", "g": "g", "ml": "ml", "un": "un"}
            unidade_base = mapa.get(unidade_embalagem, unidade_embalagem)
            unidade_input = mapa.get(unidade.lower(), unidade.lower())

            if unidade_base != unidade_input:
                continue

            # Extrair valor numérico do preço
            preco_match = re.search(r"[\d,.]+", preco_text)
            preco_valor = float(preco_match.group().replace(",", ".")) if preco_match else float("inf")

            preco_final = (preco_valor * quantidade) / quantidade_base

            melhores.append({
                "nome": nome.strip(),
                "preco": round(preco_final, 2)
            })

        if melhores:
            return min(melhores, key=lambda x: x["preco"])
        return None
    
from playwright.async_api import async_playwright
import re

class Minipreço(Supermercado):
    def __init__(self):
        super().__init__("Minipreço")

    async def buscar(self, page, produto, quantidade, unidade):
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=False)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
                    locale="pt-PT",
                    timezone_id="Europe/Lisbon",
                    java_script_enabled=True
                )
                page = await context.new_page()

                # 1. Navegar para a homepage
                await page.goto("https://www.minipreco.pt/")
                await page.wait_for_timeout(3000)

                # 2. Pesquisar o produto
                url = f"https://www.minipreco.pt/pt/search/?text={produto}"
                await page.goto(url)
                await page.wait_for_timeout(5000)

                # 3. Esperar os produtos aparecerem
                await page.wait_for_selector("div.prod_grid", timeout=8000)
                produtos_encontrados = await page.query_selector_all("div.prod_grid")
                
                melhores = []

                for prod in produtos_encontrados:
                    nome_el = await prod.query_selector("span.details")
                    preco_el = await prod.query_selector("p.price")
                    nome = await nome_el.inner_text() if nome_el else ""
                    if not produto_relevante(nome, produto):
                        continue
                    #nome = await nome_el.inner_text() if nome_el else ""
                    preco_text = await preco_el.inner_text() if preco_el else ""
                    
                    match_emb = re.search(r"([\d.,]+)\s*([a-zA-Z]+)$", nome.lower().strip())
                    if match_emb:
                        quantidade_base = float(match_emb.group(1).replace(",", "."))
                        unidade_embalagem = match_emb.group(2).lower()
                    else:
                        quantidade_base = 1.0
                        unidade_embalagem = "un"

                    mapa = {"lt": "l", "l": "l", "kg": "kg", "g": "g", "ml": "ml", "un": "un"}
                    unidade_base = mapa.get(unidade_embalagem, unidade_embalagem)
                    unidade_input = mapa.get(unidade.lower(), unidade.lower())

                    if unidade_base != unidade_input:
                        continue

                    preco_match = re.search(r"[\d,.]+", preco_text)
                    preco_valor = float(preco_match.group().replace(",", ".")) if preco_match else float("inf")

                    preco_final = (preco_valor * quantidade) / quantidade_base

                    melhores.append({
                        "nome": nome.strip(),
                        "preco": round(preco_final, 2)
                    })

                await browser.close()

                if melhores:
                    return min(melhores, key=lambda x: x["preco"])
                else:
                    return None

        except Exception as e:
            print(f"Erro ao buscar produtos Minipreço: {e}")
            return None


async def run():
    entradas = input("Digitar os produtos com quantidade e unidade separados por vírgula: ")
    produtos_input = []

    for item in entradas.split(","):
        parts = item.strip().split()
        if len(parts) < 3:
            continue
        try:
            quantidade = float(parts[-2].replace(",", "."))
        except:
            continue
        produto = " ".join(parts[:-2])
        unidade = parts[-1]
        produtos_input.append((produto, quantidade, unidade))

    supermercados = [PingoDoce(), Continente(), Aldi(), Auchan(), Minipreço()]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for produto, quantidade, unidade in produtos_input:
            print(f"Produto: {produto} ({quantidade} {unidade})")
            for mercado in supermercados:
                resultado = await mercado.buscar(page, produto, quantidade, unidade)
                if resultado:
                    print(f"{mercado.nome}: {resultado['nome']} - {resultado['preco']:.2f} €")
                else:
                    print(f"{mercado.nome}: Não encontrado.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())