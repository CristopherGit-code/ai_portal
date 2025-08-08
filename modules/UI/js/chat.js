// function createComponent(text) {
//     const el = document.createElement('div');
//     el.className = 'chat_interface';
//     el.innerText = text
//     return el
// }

// const app = document.getElementById('chat');
// ['--Model response--'].forEach(label => {
//     app.appendChild(createComponent(label))
// });

function displayParagraphs(responseString) {
  const container = document.getElementById("modules");
  container.innerHTML = "";

//   split string, the use JSON parser
  const paragraphs = responseString.split(/\n+/);

  paragraphs.forEach(text => {
    if (text.trim()) {
      const p = document.createElement("p");
      p.textContent = text.trim();
      p.className = 'response_p'
      container.appendChild(p);
    }
  });
}

document.getElementById("sendBtn").addEventListener("click", async () => {
    const userInput = document.getElementById("userInput").value;

    if (!userInput.trim()) {
        alert("Please enter something");
        return;
    }

    try {
        const response = await fetch(`http://localhost:8000/get-response?query=${encodeURIComponent(userInput)}`);
        const data = await response.json();
        displayParagraphs(data.result)
    } catch (error) {
        console.error("Error fetching data:", error);
    }
});