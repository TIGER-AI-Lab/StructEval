import os
import asyncio
import logging
from render_vue import render_vue_and_screenshot

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Sample Vue component
SAMPLE_VUE_COMPONENT = """
{
  data() {
    return {
      message: 'Hello from Vue.js',
      counter: 0,
      items: ['Apple', 'Banana', 'Cherry']
    }
  },
  methods: {
    incrementCounter() {
      this.counter++;
    }
  },
  template: `
    <div>
      <h1>{{ message }}</h1>
      <button @click="incrementCounter">Count: {{ counter }}</button>
      <ul>
        <li v-for="(item, index) in items" :key="index">{{ item }}</li>
      </ul>
    </div>
  `
}
"""

async def test_vue_rendering():
    # Set up the output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    task_id = "test_simple"
    
    # Render the Vue component
    render_score = await render_vue_and_screenshot(task_id, SAMPLE_VUE_COMPONENT, output_dir)
    
    logging.info(f"Rendering completed with score: {render_score}")
    logging.info(f"Check the output directory: {output_dir}")

if __name__ == "__main__":
    asyncio.run(test_vue_rendering()) 