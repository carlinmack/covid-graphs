document.getElementById("avg").onclick = () => {
    var exps = document.querySelectorAll(".non, .avg");
    exps.forEach(function (exp) {
        exp.classList.toggle("hidden");
    });
};
