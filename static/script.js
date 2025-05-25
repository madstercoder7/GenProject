const blob = document.getElementById("blob");

if (blob) {
    document.addEventListener("mousemove", (e) => {
        const { clientX, clientY } = e;
        blob.style.transform = `translate(${clientX - 200}px, ${clientY - 200}px)`;
    });
}
