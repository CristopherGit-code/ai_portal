function createComponent(text){
    const el = document.createElement('div');
    el.className = 'chat_interface';
    el.innerText = text
    return el
}

const app = document.getElementById('chat');
['This is an example','Of how to get a chat','From the JS code'].forEach(label => {
    app.appendChild(createComponent(label))
});