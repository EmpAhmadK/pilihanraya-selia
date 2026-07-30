// Currently all interactivity (toggling the seat edit panel) is handled
// inline in election.html via the toggleSeatEdit() function, and all saves
// are done through normal form POSTs so that this stays simple and robust
// even without JavaScript enabled for the write path.
document.addEventListener("DOMContentLoaded", function () {
  // Confirm before submitting a "Rasmi" save, since ticking it triggers a
  // permanent Wikidata edit (adding P991 / P1697) that this tool will not
  // undo automatically.
  document.querySelectorAll(".seat-edit-form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      const rasmiBox = form.querySelector('input[name="rasmi"]');
      if (rasmiBox && rasmiBox.checked && !rasmiBox.disabled) {
        const ok = confirm(
          "Anda akan mengesahkan keputusan ini sebagai RASMI. " +
          "Ini akan menambah pemenang (P991) dan jumlah undi sah (P1697) " +
          "pada item Wikidata. Teruskan?"
        );
        if (!ok) e.preventDefault();
      }
    });
  });
});
