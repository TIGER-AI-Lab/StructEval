// Leaderboard data from the paper
const leaderboardData = [
  // Open Source Models
  {
      model: "Llama-3.1-8B-Instruct",
      type: "open_source",
      se_t_gen: 60.22,
      se_t_conv: 71.26,
      se_v_gen: 54.44,
      se_v_conv: 61.15,
      average: 61.77
  },
  {
      model: "Meta-Llama-3-8B-Instruct",
      type: "open_source",
      se_t_gen: 49.18,
      se_t_conv: 53.65,
      se_v_gen: 46.61,
      se_v_conv: 56.91,
      average: 51.59
  },
  {
      model: "Phi-3-mini-128k-instruct",
      type: "open_source",
      se_t_gen: 47.39,
      se_t_conv: 29.78,
      se_v_gen: 44.77,
      se_v_conv: 41.23,
      average: 40.79
  },
  {
      model: "Phi-4-mini-instruct",
      type: "open_source",
      se_t_gen: 51.38,
      se_t_conv: 72.39,
      se_v_gen: 51.62,
      se_v_conv: 52.48,
      average: 56.97
  },
  {
      model: "Qwen2.5-7B-Instruct",
      type: "open_source",
      se_t_gen: 59.21,
      se_t_conv: 62.18,
      se_v_gen: 53.28,
      se_v_conv: 61.43,
      average: 59.03
  },
  {
      model: "Qwen3-4B",
      type: "open_source",
      se_t_gen: 64.95,
      se_t_conv: 81.13,
      se_v_gen: 57.00,
      se_v_conv: 65.08,
      average: 67.04
  },
  // Closed Source Models
  {
      model: "Gemini-1.5-pro",
      type: "proprietary",
      se_t_gen: 88.07,
      se_t_conv: 74.24,
      se_v_gen: 58.11,
      se_v_conv: 66.59,
      average: 71.75
  },
  {
      model: "Gemini-2.0-flash",
      type: "proprietary",
      se_t_gen: 72.42,
      se_t_conv: 72.20,
      se_v_gen: 53.62,
      se_v_conv: 51.97,
      average: 62.55
  },
  {
      model: "GPT-4.1-mini",
      type: "proprietary",
      se_t_gen: 92.57,
      se_t_conv: 75.63,
      se_v_gen: 64.30,
      se_v_conv: 70.04,
      average: 75.64
  },
  {
      model: "GPT-4o",
      type: "proprietary",
      se_t_gen: 91.52,
      se_t_conv: 73.95,
      se_v_gen: 65.39,
      se_v_conv: 73.20,
      average: 76.02
  },
  {
      model: "GPT-4o-mini",
      type: "proprietary",
      se_t_gen: 79.86,
      se_t_conv: 75.57,
      se_v_gen: 60.77,
      se_v_conv: 76.54,
      average: 73.19
  },
  {
      model: "o1-mini",
      type: "proprietary",
      se_t_gen: 88.12,
      se_t_conv: 81.82,
      se_v_gen: 61.98,
      se_v_conv: 70.40,
      average: 75.58
  }
];

document.addEventListener('DOMContentLoaded', function() {
  loadTableData();
  setupCharts();
  
  // Smooth scrolling for navigation links
  const navLinks = document.querySelectorAll('a[href^="#"]');
  navLinks.forEach(link => {
      link.addEventListener('click', function(e) {
          e.preventDefault();
          const targetId = this.getAttribute('href');
          const targetSection = document.querySelector(targetId);
          if (targetSection) {
              targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
      });
  });
});

function loadTableData() {
  const tbody = document.querySelector('#structeval-table tbody');
  tbody.innerHTML = '';

  // Sort by average score descending
  // const sortedData = [...leaderboardData].sort((a, b) => b.average - a.average);

  leaderboardData.forEach((row) => {
      const tr = document.createElement('tr');
      tr.classList.add(row.type);
      
      // Find best and second best for styling
      const allScores = [row.se_t_gen, row.se_t_conv, row.se_v_gen, row.se_v_conv, row.average];
      
      tr.innerHTML = `
          <td><b>${row.model}</b></td>
          <td>${row.type === 'open_source' ? 'Open' : 'Closed'}</td>
          <td>${formatScore(row.se_t_gen)}</td>
          <td>${formatScore(row.se_t_conv)}</td>
          <td>${formatScore(row.se_v_gen)}</td>
          <td>${formatScore(row.se_v_conv)}</td>
          <td><b>${formatScore(row.average)}</b></td>
      `;
      tbody.appendChild(tr);
  });
  
  // Add sorting functionality
  initializeSorting();
}

function formatScore(score) {
  return score.toFixed(2);
}

function initializeSorting() {
  const headers = document.querySelectorAll('#structeval-table thead th.sortable');
  headers.forEach(header => {
      header.addEventListener('click', function() {
          sortTable(this);
      });
  });
}

function sortTable(header) {
  const table = document.getElementById('structeval-table');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const headerIndex = Array.from(header.parentNode.children).indexOf(header);
  
  // Determine sort direction
  const isAscending = header.classList.contains('asc');
  
  rows.sort((a, b) => {
      let aValue, bValue;
      
      if (headerIndex === 0) { // Model name
          aValue = a.cells[0].textContent.trim();
          bValue = b.cells[0].textContent.trim();
          return isAscending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
      } else if (headerIndex === 1) { // Type
          aValue = a.cells[1].textContent.trim();
          bValue = b.cells[1].textContent.trim();
          return isAscending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
      } else { // Numeric values
          aValue = parseFloat(a.cells[headerIndex].textContent);
          bValue = parseFloat(b.cells[headerIndex].textContent);
          return isAscending ? aValue - bValue : bValue - aValue;
      }
  });
  
  // Clear all sort indicators
  document.querySelectorAll('#structeval-table thead th').forEach(th => {
      th.classList.remove('asc', 'desc');
  });
  
  // Set new sort indicator
  header.classList.add(isAscending ? 'desc' : 'asc');
  
  // Re-append rows
  rows.forEach(row => tbody.appendChild(row));
}

function setupCharts() {
  // Task Type Performance Chart
  const taskTypeCtx = document.getElementById('task_type_chart');
  if (taskTypeCtx) {
      const avgScores = {
          'T-Gen': leaderboardData.reduce((sum, d) => sum + d.se_t_gen, 0) / leaderboardData.length,
          'T-Conv': leaderboardData.reduce((sum, d) => sum + d.se_t_conv, 0) / leaderboardData.length,
          'V-Gen': leaderboardData.reduce((sum, d) => sum + d.se_v_gen, 0) / leaderboardData.length,
          'V-Conv': leaderboardData.reduce((sum, d) => sum + d.se_v_conv, 0) / leaderboardData.length
      };

      new Chart(taskTypeCtx, {
          type: 'bar',
          data: {
              labels: Object.keys(avgScores),
              datasets: [{
                  label: 'Average Score (%)',
                  data: Object.values(avgScores),
                  backgroundColor: [
                      'rgba(54, 162, 235, 0.8)',
                      'rgba(54, 162, 235, 0.5)',
                      'rgba(255, 99, 132, 0.8)',
                      'rgba(255, 99, 132, 0.5)'
                  ],
                  borderColor: [
                      'rgba(54, 162, 235, 1)',
                      'rgba(54, 162, 235, 1)',
                      'rgba(255, 99, 132, 1)',
                      'rgba(255, 99, 132, 1)'
                  ],
                  borderWidth: 2
              }]
          },
          options: {
              responsive: true,
              plugins: {
                  legend: {
                      display: false
                  },
                  title: {
                      display: true,
                      text: 'Average Performance by Task Type',
                      font: {
                          size: 16
                      }
                  }
              },
              scales: {
                  y: {
                      beginAtZero: true,
                      max: 100,
                      ticks: {
                          callback: function(value) {
                              return value + '%';
                          }
                      }
                  }
              }
          }
      });
  }

  // Challenging Formats Chart
  const formatDifficultyCtx = document.getElementById('format_difficulty_chart');
  if (formatDifficultyCtx) {
      // Data from paper showing challenging formats
      const challengingFormats = {
          'Text→TOML': 35.8,
          'Text→Mermaid': 18.9,
          'Text→SVG': 48.7,
          'Matplotlib→TikZ': 28.4,
          'YAML→XML': 41.2,
          'CSV→YAML': 45.6
      };

      new Chart(formatDifficultyCtx, {
          type: 'bar',
          data: {
              labels: Object.keys(challengingFormats),
              datasets: [{
                  label: 'Average Score (%)',
                  data: Object.values(challengingFormats),
                  backgroundColor: 'rgba(255, 159, 64, 0.8)',
                  borderColor: 'rgba(255, 159, 64, 1)',
                  borderWidth: 2
              }]
          },
          options: {
              indexAxis: 'y', // This makes the bar chart horizontal
              responsive: true,
              plugins: {
                  legend: {
                      display: false
                  },
                  title: {
                      display: true,
                      text: 'Most Challenging Format Transformations',
                      font: {
                          size: 16
                      }
                  }
              },
              scales: {
                  x: {
                      beginAtZero: true,
                      max: 100,
                      ticks: {
                          callback: function(value) {
                              return value + '%';
                          }
                      }
                  }
              }
          }
      });
  }
}

// Navbar burger functionality
document.addEventListener('DOMContentLoaded', () => {
  const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);
  if ($navbarBurgers.length > 0) {
      $navbarBurgers.forEach(el => {
          el.addEventListener('click', () => {
              const $target = document.querySelector('.navbar-menu');
              el.classList.toggle('is-active');
              $target.classList.toggle('is-active');
          });
      });
  }
});
