function buildCard(props) {
  const container = document.getElementById("modules")

  const card = document.createElement('div')
  card.className = 'card'

  const title = document.createElement('h3')
  title.textContent = props.title
  const body = document.createElement('p')
  body.textContent = props.content

  card.appendChild(title)
  card.appendChild(body)

  container.appendChild(card)
}

function buildChart(props) {
  const container = document.getElementById("modules")

  const chart = document.createElement('canvas')
  chart.className = 'chart'
  chart.id = "bar"
  chart.width = 400
  chart.height = 200
  container.appendChild(chart)

  new Chart(chart.getContext('2d'), {
    type: props.chartType,
    data: {
      labels: props.labels.map(item => item.label),
      datasets: [{
        label: props.title,
        data: props.data.map(item => item.datakey),
        backgroundColor: [
          '#ff6384', '#36a2eb', '#ffcd56', '#4bc0c0', '#9966ff', '#ff9f40',
          '#8bc34a', '#00bcd4', '#d84315'
        ]
      }]
    },
    options: {
      responsive: false,
      plugins: {
        title: {
          display: true,
          text: props.title
        }
      },
      scales: props.chartType === 'bar' ? {
        y: {
          beginAtZero: true
        }
      } : {}
    }
  })
}

function buildResponse(response) {
  const container = document.getElementById('modules');
  container.innerHTML = '';

  try {
    response.forEach(component => {
      console.log(component)
      switch (component.component) {
        case 'card':
          buildCard(component.props)
          break
        case 'chart':
          buildChart(component.props)
          break
        default:
          break
      }
    })
  } catch (error) {
    console.log(error)
  }
}

// Loader for user -------

let loaderInterval

function showLoader(containerId = "modules") {
  clearInterval(loaderInterval)

  const container = document.getElementById(containerId);
  if (!container) return

  const phrases = [
    "Validating phrase...",
    "Getting agent plans...",
    "Selecting best agents...",
    "Doing awesome agent team up!",
    "Great visuals comming..."
  ]

  let index = 0;
  container.innerHTML = `
    <div class="loader">
      <div class="loader-dots"><span></span><span></span><span></span></div>
      <p id="loader-text">${phrases[index]}</p>
    </div>
  `

  loaderInterval = setInterval(() => {
    if (index < phrases.length - 1) {
      index++;
      const textEl = document.getElementById("loader-text");
      if (textEl) textEl.textContent = phrases[index];
    }
  }, 20000)
}

function hideLoader() {
  clearInterval(loaderInterval)
  loaderInterval = null
}

// ------------ END loader

document.getElementById("sendBtn").addEventListener("click", async () => {
  const userInput = document.getElementById("userInput").value

  showLoader() // just for visual representation

  if (!userInput.trim()) {
    alert("Please enter something")
    return
  }

  try {
    const response = await fetch(`http://localhost:8000/get-response?query=${encodeURIComponent(userInput)}`)
    const data = await response.json()
    hideLoader()
    buildResponse(data.result)
  } catch (error) {
    hideLoader()
    console.error("Error fetching data:", error)
    document.getElementById('response').textContent = error
  }
});