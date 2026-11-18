import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

URL_CONCURSOS = "https://cfe.mx"
# Lee la palabra clave desde GitHub Actions, o usa "" para traer todos los vigentes
PALABRA_CLAVE = os.getenv("PALABRA_CLAVE", "").strip()

def revisar_concursos_cfe():
    resultados = []
    encabezados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("1. Abriendo portal de concursos CFE...")
        page.goto(URL_CONCURSOS, timeout=60000)
        page.wait_for_load_state("networkidle")

        # Seleccionar Estatus: Vigente
        print("2. Seleccionando estatus 'Vigente'...")
        try:
            select_estatus = page.locator("select").filter(has_text="Estatus del procedimiento").first
            if select_estatus.is_visible():
                select_estatus.select_option(label="Vigente")
            else:
                dropdown_estatus = page.locator("text='Estatus del procedimiento...'").first
                if dropdown_estatus.is_visible():
                    dropdown_estatus.click()
                    time.sleep(0.5)
                    page.locator("li:has-text('Vigente'), option:has-text('Vigente'), span:has-text('Vigente')").first.click()
        except Exception as e:
            print(f"Aviso estatus: {e}")

        page.keyboard.press("Escape")
        time.sleep(0.5)

        if PALABRA_CLAVE:
            print(f"3. Buscando '{PALABRA_CLAVE}' en Descripción...")
            campo_desc = page.locator(
                "input[placeholder*='Descrip' i]:visible, "
                "input[name*='Descrip' i]:visible, "
                "input[id*='Descrip' i]:visible"
            ).first

            if campo_desc.is_visible():
                campo_desc.fill(PALABRA_CLAVE)
            else:
                inputs_visibles = page.locator("input[type='text']:visible")
                if inputs_visibles.count() > 1:
                    inputs_visibles.nth(1).fill(PALABRA_CLAVE)
                else:
                    inputs_visibles.first.fill(PALABRA_CLAVE)

        print("4. Presionando botón Buscar...")
        btn_buscar = page.locator(
            "button:has-text('Buscar'):visible, "
            "input[value*='Buscar' i]:visible, "
            "a:has-text('Buscar'):visible"
        ).first

        if btn_buscar.is_visible():
            btn_buscar.click(force=True)
        else:
            page.keyboard.press("Enter")

        print("5. Esperando resultados...")
        try:
            cargando = page.locator("text='Cargando...'").first
            if cargando.is_visible(timeout=3000):
                cargando.wait_for(state="hidden", timeout=45000)
        except Exception:
            pass

        try:
            page.wait_for_selector("table tbody tr td", timeout=30000)
            time.sleep(2)
        except Exception:
            print("Aviso: Tiempo de espera agotado para la tabla.")

        ths = page.locator("table thead th")
        if ths.count() == 0:
            ths = page.locator("table tr th")

        if ths.count() > 0:
            encabezados = [
                " ".join(ths.nth(i).inner_text().split())
                for i in range(ths.count())
                if ths.nth(i).inner_text().strip() != ""
            ]

        filas = page.locator("table tbody tr")
        for i in range(filas.count()):
            celdas = filas.nth(i).locator("td")
            datos_fila = [" ".join(celdas.nth(j).inner_text().split()) for j in range(celdas.count())]
            if any(datos_fila) and "No existen resultados" not in "".join(datos_fila):
                resultados.append(datos_fila)

        page.screenshot(path="captura_cfe.png", full_page=True)
        browser.close()

    if resultados:
        num_columnas = len(resultados[0])
        if encabezados and len(encabezados) == num_columnas:
            df = pd.DataFrame(resultados, columns=encabezados)
        elif encabezados and len(encabezados) > num_columnas:
            df = pd.DataFrame(resultados, columns=encabezados[:num_columnas])
        else:
            df = pd.DataFrame(resultados[1:], columns=resultados[0])

        col_estatus = [c for c in df.columns if "estatus" in c.lower()]
        if col_estatus:
            df = df[df[col_estatus[0]].str.contains("Vigente", case=False, na=False)]

        df.to_csv("concursos_cfe_vigentes.csv", index=False, encoding="utf-8-sig")
        print(f"¡Éxito! {len(df)} registros guardados en 'concursos_cfe_vigentes.csv'.")
    else:
        print("0 registros encontrados.")

if __name__ == "__main__":
    revisar_concursos_cfe()
