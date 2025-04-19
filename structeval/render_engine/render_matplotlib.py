import os
import re
import logging
import tempfile
import traceback

import matplotlib.pyplot as plt

def extract_matplotlib_from_code_tag(generation):
    match = re.search(r"<code>(.*?)</code>", generation, re.DOTALL)
    return match.group(1) if match else None

def render_matplotlib_and_screenshot(task_id, python_code, img_output_path):
    """
    Executes Python code that generates a matplotlib figure and saves the figure as a PNG.
    Returns 1 if successful, 0 otherwise.
    """
    os.makedirs(img_output_path, exist_ok=True)
    render_score = 0

    if not python_code:
        logging.warning(f"No matplotlib code found for task {task_id}")
        return render_score

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "plot_script.py")
            output_path = os.path.join(img_output_path, f"{task_id}.png")

            # Append savefig line to ensure image is saved
            full_script = (
                "import matplotlib.pyplot as plt\n"
                + python_code.strip()
                + f"\nplt.savefig(r'{output_path}', bbox_inches='tight')\nplt.close()"
            )

            # Write code to a temporary script file
            with open(script_path, "w") as f:
                f.write(full_script)

            # Execute the script
            os.system(f"python {script_path}")
            if os.path.exists(output_path):
                logging.info(f"Matplotlib screenshot saved: {output_path}")
                render_score = 1
            else:
                logging.error(f"Matplotlib image not generated for task {task_id}")
    except Exception as e:
        logging.error(f"Matplotlib rendering failed for task {task_id}: {e}")
        traceback.print_exc()

    return render_score
