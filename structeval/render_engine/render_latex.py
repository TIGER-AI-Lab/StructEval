import os, re, subprocess, tempfile, logging, shutil, time
from pdf2image import convert_from_path

COMMON_COLOR_DEFS = r"""
\providecolor{navy}{RGB}{0,0,128}
\providecolor{teal}{RGB}{0,128,128}
\providecolor{orange}{RGB}{255,165,0}
\providecolor{purple}{RGB}{128,0,128}
\providecolor{brown}{RGB}{150,75,0}
"""


# ---------------------------- helper -------------------------------- #
def _build_document(body: str) -> str:
    """
    Wrap a TikZ/LaTeX fragment in a minimal standalone document.
    Loads the packages most TikZ pictures need.
    """
    packages = r"""
\usepackage{amsmath,amssymb,graphicx,xcolor}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usetikzlibrary{arrows.meta,positioning,calc,shapes.geometric,shapes.misc,fit,backgrounds,patterns,plotmarks,matrix}
""" + COMMON_COLOR_DEFS + r"""
"""
    return (
        r"\documentclass[tikz,border=2pt]{standalone}" "\n"
        f"{packages}\n"
        r"\begin{document}"          "\n"
        f"{body}\n"
        r"\end{document}"            "\n"
    )


def _inject_common_preamble(latex_code: str) -> str:
    if r"\providecolor{navy}" in latex_code:
        return latex_code
    begin_doc = re.search(r"\\begin\{document\}", latex_code)
    if begin_doc:
        return (
            latex_code[: begin_doc.start()]
            + COMMON_COLOR_DEFS
            + "\n"
            + latex_code[begin_doc.start() :]
        )
    return COMMON_COLOR_DEFS + "\n" + latex_code


# ---------------------------- core ---------------------------------- #
def _latex_engines(latex_code: str):
    engines = []
    if shutil.which("pdflatex"):
        engines.append("pdflatex")
    if shutil.which("lualatex"):
        engines.append("lualatex")

    needs_unicode_engine = bool(
        re.search(r"\\(?:usepackage\{fontspec\}|setmainfont|setsansfont|setmonofont)", latex_code)
    )
    if needs_unicode_engine and "lualatex" in engines:
        engines = ["lualatex"] + [engine for engine in engines if engine != "lualatex"]

    return engines


def _sanitize_for_pdflatex(latex_code: str):
    latex_code = re.sub(
        r"\\usepackage(?:\[[^\]]*\])?\{fontspec\}\s*",
        "",
        latex_code,
    )
    latex_code = re.sub(
        r"\\(?:setmainfont|setsansfont|setmonofont)(?:\[[^\]]*\])?\{[^{}]*\}\s*",
        "",
        latex_code,
    )
    return latex_code


def _compile_with_engine(engine: str, tex_file: str, pdf_file: str, tmp: str, remaining):
    cmd = [
        engine,
        "-interaction=nonstopmode",
        "-file-line-error",
        "-output-directory",
        tmp,
        tex_file,
    ]
    proc = None
    for _ in range(2):
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=remaining(),
        )
        if remaining() <= 1:
            break
    pdf_ok = os.path.isfile(pdf_file) and os.path.getsize(pdf_file) > 0
    return pdf_ok, proc


def render_latex_to_png(
    latex_code: str,
    output_path: str,
    task_id: str,
    dpi: int = 300,
    timeout_seconds: int = 45,
) -> bool:
    """
    Compile LaTeX → PDF → PNG.  Returns True on success.
    """
    start_time = time.time()
    def _remaining():
        return max(1, int(timeout_seconds - (time.time() - start_time)))

    screenshot_path = os.path.join(output_path, f"{task_id}.png")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tex_file = os.path.join(tmp, "doc.tex")
            pdf_file = os.path.join(tmp, "doc.pdf")

            # Wrap a fragment only if it has no \begin{document}
            if r"\begin{document}" not in latex_code:
                latex_code = _build_document(latex_code)   # ★
            latex_code = _inject_common_preamble(latex_code)

            with open(tex_file, "w", encoding="utf8") as f:
                f.write(latex_code)

            # ----- compile: try Tectonic first, then local TeX engines ----------
            pdf_ok = False
            last_proc = None
            if shutil.which("tectonic"):
                try:
                    subprocess.run(
                        ["tectonic", "-X", "compile",
                         "--outdir", tmp, tex_file],
                        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        timeout=_remaining()
                    )
                    pdf_ok = os.path.isfile(pdf_file) and os.path.getsize(pdf_file) > 0
                except subprocess.CalledProcessError:
                    logging.warning("Tectonic failed – falling back to pdflatex.")

            if not pdf_ok:
                for engine in _latex_engines(latex_code):
                    try:
                        engine_code = (
                            _sanitize_for_pdflatex(latex_code)
                            if engine == "pdflatex"
                            else latex_code
                        )
                        with open(tex_file, "w", encoding="utf8") as f:
                            f.write(engine_code)
                        pdf_ok, last_proc = _compile_with_engine(
                            engine, tex_file, pdf_file, tmp, _remaining
                        )
                    except subprocess.TimeoutExpired:
                        logging.warning("%s timed out for %s", engine, task_id)
                        continue
                    if pdf_ok:
                        break

                if not pdf_ok:
                    if last_proc is not None:
                        logging.warning("LaTeX produced no PDF. Last run log:")
                        logging.warning(last_proc.stdout.decode(errors="ignore")[-1000:])
                        logging.warning(last_proc.stderr.decode(errors="ignore")[-200:])
                    raise RuntimeError("LaTeX failed without output")

            # sanity‑check that the PDF exists now
            if not os.path.isfile(pdf_file) or os.path.getsize(pdf_file) == 0:
                raise RuntimeError("pdflatex/tectonic produced no usable PDF file")

            images = convert_from_path(pdf_file, dpi=dpi, first_page=1, last_page=1)

            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"Rendering exceeded {timeout_seconds} seconds")

            if not images:
                raise RuntimeError("No page produced by pdflatex")
            
            # ensure the output directory itself exists
            if not os.path.isdir(output_path):
                os.makedirs(output_path, exist_ok=True)

            images[0].save(screenshot_path, "PNG")
            print(f"✅ Saved screenshot for {task_id} → {screenshot_path}")
            return 1

    except subprocess.CalledProcessError as e:           # ★ show real log
        print("❌ pdflatex error:")
        print(e.stdout.decode(errors="ignore"))
        print(e.stderr.decode(errors="ignore"))
    except TimeoutError as e:
        print(f"⏰ Timeout: {e}")
    except Exception as e:
        print(f"❌ LaTeX render failed: {e}")

    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)

    return 0

def extract_latex_from_code_tag(generation, output_type):
    """
    Extract LaTeX code from <code> tags and clean it up.
    Removes control characters and converts double backslashes to single ones.
    """
    begin_end_pat = (
        r"<\|BEGIN_CODE\|\>[ \t]*\n?"        # literal opener (pipes escaped)
        r"(?P<payload1>.*?)"                 # everything after it…
        r"(?:<\|END_CODE\|\>|$)"             # …until END tag *or* EOS
    )

    # 2)  ``` fenced block  (closing fence optional)
    fence_pat = (
        rf"```(?:{re.escape(output_type)}|[^\n]*)[ \t]*\n"  # header
        r"(?P<payload2>.*?)"                               # payload
        r"(?:```|$)"                                       # end fence or EOS
    )

    pattern = rf"(?:{begin_end_pat})|(?:{fence_pat})"
    m = re.search(pattern, generation, re.DOTALL | re.IGNORECASE)
    code = generation.strip()
    if m:
        # whichever group matched, return it
        payload = m.group("payload1") or m.group("payload2")
        code = payload.strip()

    if code:
        # Remove control characters (ASCII 0-31, excluding \t, \n, \r)
        code = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', code)

    return code
