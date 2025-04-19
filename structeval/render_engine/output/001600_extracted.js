// Template for Vue application
const { createApp } = Vue;

// Vue component from task 001600
const App = 
{
  name: 'RecipeComponent',
  data() {
    return {
      ingredients: ['2 eggs', '1 cup of flour', '1/2 cup of milk'],
      cookingSteps: ['Whisk the eggs and milk together.','Gradually add the flour and mix until smooth.','Pour into pan and cook until golden.'],
      newIngredient: ''
    };
  },
  computed: {
    numberOfSteps() {
      return this.cookingSteps.length;
    }
  },
  methods: {
    addIngredient() {
      if (this.newIngredient.trim() !== '') {
        this.ingredients.push(this.newIngredient.trim());
        this.newIngredient = '';
      }
    }
  },
  template: `<div><h2>Recipe Instructions</h2><input v-model="newIngredient" placeholder="Enter additional ingredient" /><button @click="addIngredient">Add Ingredient</button><ol><li v-for="(item, index) in ingredients" :key="index">{{ item }}</li></ol><p>Total Ingredients: {{ ingredients.length }}</p><div v-for="(step, index) in cookingSteps" :key="index" class="step">{{ index + 1 }}. {{ step }}</div></div>`
}
;

// Mount the app
const app = createApp(App);
app.mount('#app');