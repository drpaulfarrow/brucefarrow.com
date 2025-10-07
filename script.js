const btn = document.getElementById('greetButton');
const msg = document.getElementById('greetMessage');

if (btn && msg) {
    btn.addEventListener('click', () => {
        msg.textContent = "Hello, Bruce! Have a great day!";
        msg.classList.remove('visible');
        // trigger reflow to restart animation
        void msg.offsetWidth;
        msg.classList.add('visible');
    });
}