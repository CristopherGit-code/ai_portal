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

  const data = props.data.map(item => item.datakey)
  const labels = props.labels.map(item => item.label)
  const type = props.chartType
  const chartTitle = props.title

  new Chart(chart.getContext('2d'), {
    type: type,
    data: {
      labels: labels,
      datasets: [{
        label: chartTitle,
        data: data,
        backgroundColor: [
          '#ff6384', '#36a2eb', '#ffcd56', '#4bc0c0', '#9966ff', '#ff9f40',
          '#8bc34a', '#00bcd4', '#d84315'
        ]
      }]
    },
    options: {
      responsive: false,
      plugins:{
        title:{
          display:true,
          text:chartTitle
        }
      },
      scales: type === 'bar' ? {
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

document.getElementById("sendBtn").addEventListener("click", async () => {
  const userInput = document.getElementById("userInput").value;

  if (!userInput.trim()) {
    alert("Please enter something")
    return;
  }

  try {
    const response = await fetch(`http://localhost:8000/get-response?query=${encodeURIComponent(userInput)}`)
    const data = await response.json()
    buildResponse(data.result)
  } catch (error) {
    console.error("Error fetching data:", error)
    document.getElementById('response').textContent = error
  }
});