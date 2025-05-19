// Template for Vue application
const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

// Simple markdown-like renderer for development purposes
const markdownToHtml = (text) => {
  if (!text) return '';
  
  // Basic markdown conversion
  return text
    // Convert headers
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    // Convert bold/italic
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    // Convert code blocks
    .replace(/```([^`]+)```/gim, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/gim, '<code>$1</code>')
    // Convert lists
    .replace(/^\s*- (.*$)/gim, '<li>$1</li>')
    .replace(/^\s*\d+\. (.*$)/gim, '<li>$1</li>')
    // Convert blockquotes
    .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
    // Convert paragraphs
    .replace(/\n\s*\n/gim, '</p><p>')
    // Convert line breaks
    .replace(/\n/gim, '<br>');
};

// Your Vue component will be defined here
const App = {
  data() {
    return {
      count: 0,
      message: 'Vue Template'
    }
  },
  methods: {
    increment() {
      this.count++
    },
    decrement() {
      if (this.count > 0) {
        this.count--
      }
    },
    reset() {
      this.count = 0
    },
    renderMarkdown(text) {
      return markdownToHtml(text);
    }
  },
  template: `
    <div>
      <h1>{{ message }}</h1>
      <p>A simple Vue.js template</p>
      
      <div class="counter">
        <button @click="decrement">-</button>
        <div class="count">{{ count }}</div>
        <button @click="increment">+</button>
        <button type="reset" @click="reset">Reset</button>
      </div>
      
      <p v-if="count > 10">Getting high!</p>
      <p v-else-if="count > 0">Keep counting!</p>
      <p v-else>Let's start counting!</p>
    </div>
  `
};

// Mount the app
const app = createApp(App);
app.mount('#app'); 
