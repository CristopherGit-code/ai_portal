function createComponent(text){
    const el = document.createElement('div');
    el.className = 'chat_interface';
    el.innerText = text
    return el
}

const app = document.getElementById('chat');
['--Model response--'].forEach(label => {
    app.appendChild(createComponent(label))
});