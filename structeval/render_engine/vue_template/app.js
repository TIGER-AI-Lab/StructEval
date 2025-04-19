// Template for Vue application
const { createApp } = Vue;

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