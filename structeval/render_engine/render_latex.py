import os, re, subprocess, tempfile, logging, shutil, time
from pdf2image import convert_from_path


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
"""
    return (
        r"\documentclass[tikz,border=2pt]{standalone}" "\n"
        f"{packages}\n"
        r"\begin{document}"          "\n"
        f"{body}\n"
        r"\end{document}"            "\n"
    )


# ---------------------------- core ---------------------------------- #
def render_latex_to_png(latex_code: str, output_path: str, task_id: str, dpi: int = 300) -> bool:
    """
    Compile LaTeX → PDF → PNG.  Returns True on success.
    """
    # ---- 20‑second overall timeout ----

    # print(output_path)
    start_time = time.time()
    def _remaining():
        """seconds left before hitting the 20‑second wall (≥1)."""
        return max(1, int(20 - (time.time() - start_time)))

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tex_file = os.path.join(tmp, "doc.tex")
            pdf_file = os.path.join(tmp, "doc.pdf")

            # Wrap a fragment only if it has no \begin{document}
            if r"\begin{document}" not in latex_code:
                latex_code = _build_document(latex_code)   # ★

            with open(tex_file, "w", encoding="utf8") as f:
                f.write(latex_code)

            # ----- compile: try Tectonic first, then pdflatex ----------
            pdf_ok = False
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
                # Run pdflatex (no -halt-on-error) and DO NOT stop on non‑zero exit status.
                cmd = ["pdflatex", "-interaction=nonstopmode", "-file-line-error",
                       "-output-directory", tmp, tex_file]

                for _ in range(2):         # two passes for references/TikZ sizes
                    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=_remaining())

                # even if return‑code ≠ 0, accept the run provided a PDF exists
                pdf_ok = os.path.isfile(pdf_file) and os.path.getsize(pdf_file) > 0
                if not pdf_ok:
                    # show log excerpt then bail
                    print("❌ pdflatex produced no PDF. Last run log:")
                    print(proc.stdout.decode(errors="ignore")[-1000:])  # tail
                    print(proc.stderr.decode(errors="ignore")[-200:])
                    raise RuntimeError("pdflatex failed without output")

            # sanity‑check that the PDF exists now
            if not os.path.isfile(pdf_file) or os.path.getsize(pdf_file) == 0:
                raise RuntimeError("pdflatex/tectonic produced no usable PDF file")

            images = convert_from_path(pdf_file, dpi=dpi, first_page=1, last_page=1)

            # abort if the total render time has exceeded 20 s
            if time.time() - start_time > 6:
                raise TimeoutError("Rendering exceeded 6 seconds")

            if not images:
                raise RuntimeError("No page produced by pdflatex")
            
            # ensure the output directory itself exists
            if not os.path.isdir(output_path):
                os.makedirs(output_path, exist_ok=True)

            screenshot_path = os.path.join(output_path, f"{task_id}.png")
            images[0].save(screenshot_path, "PNG")
            print(f"✅ Saved screenshot for {task_id} → {screenshot_path}")
            return 1

    except subprocess.CalledProcessError as e:           # ★ show real log
        print("❌ pdflatex error:")
        print(e.stdout.decode(errors="ignore"))
        print(e.stderr.decode(errors="ignore"))
    except Exception as e:
        print(f"❌ LaTeX render failed: {e}")
    except TimeoutError as e:
        print(f"⏰ Timeout: {e}")
        return 0

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
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if m:
        # whichever group matched, return it
        payload = m.group("payload1") or m.group("payload2")
        code = payload.strip()

    if code:
        # Remove control characters (ASCII 0-31, excluding \t, \n, \r)
        code = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', code)

    return code
