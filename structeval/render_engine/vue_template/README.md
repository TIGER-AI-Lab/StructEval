# Vue.js Template

A simple Vue.js template using CDN for quick prototyping without a build step.

## Overview

This template is used by the render_engine module to render Vue components for testing and evaluation. It provides a basic setup that loads Vue.js from CDN and renders a component.

## Files

- `index.html` - The main HTML file with Vue.js imported from CDN
- `app.js` - Contains the Vue application code and mounting logic

## How the Renderer Works

The rendering process:

1. The renderer copies this template to a temporary directory
2. It injects the Vue component code to test into app.js
3. A Python HTTP server serves the template
4. Playwright navigates to the page and takes a screenshot
5. The screenshot is saved for evaluation

## Default Component

The template includes a simple counter component to demonstrate Vue functionality:

- Increment/decrement buttons
- Reset functionality
- Conditional rendering based on counter value

## Project Structure

- `index.html` - The main HTML file with Vue.js imported from CDN
- `app.js` - Contains the Vue application code
- `README.md` - This file

## Getting Started

1. Clone this repository
2. Open `index.html` in your browser
3. Edit `app.js` to customize the Vue application

## Features

- No build step required
- Uses Vue 3 from CDN
- Simple counter example included
- Easy to extend with additional components

## Adding Components

To add more components, you can extend the app.js file:

```javascript
// Define a new component
app.component('my-component', {
  template: `
    <div>
      <!-- Your component template goes here -->
    </div>
  `,
  data() {
    return {
      // Your component data goes here
    }
  },
  methods: {
    // Your component methods go here
  }
})
```

Then use it in your main App template:

```html
<my-component></my-component>
``` 