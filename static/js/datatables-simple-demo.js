window.addEventListener('DOMContentLoaded', event => {
    // Simple-DataTables
    // https://github.com/fiduswriter/Simple-DataTables/wiki

    const datatablesSimple = document.getElementById('datatablesSimple');
    if (datatablesSimple) {
        var datatable = new simpleDatatables.DataTable(datatablesSimple);

      

        document.querySelectorAll(".export").forEach(function(el) {
        el.addEventListener("click", function(e) {
            var type = el.dataset.type;

            var data = {
            type: type,
            filename: "my-" + type,
            };

            if ( type === "csv" ) {
            data.columnDelimiter = ",";
            }

            datatable.export(data);
        });
        });
  
    }
    const datatablesSimple2 = document.getElementById('datatableSimple2');
    if (datatablesSimple2){
        var datatable2 = new simpleDatatables.DataTable(datatablesSimple2);
        document.querySelectorAll(".export2").forEach(function(el) {
            el.addEventListener("click", function(e) {
                var type = el.dataset.type;
    
                var data = {
                type: type,
                filename: "my-" + type,
                };
    
                if ( type === "csv" ) {
                data.columnDelimiter = ",";
                }
    
                datatable2.export(data);
            });
            });
    }
});


