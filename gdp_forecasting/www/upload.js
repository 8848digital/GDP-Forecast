(function ($) {
    document.addEventListener("DOMContentLoaded", function() {
        const dropdownItems = document.querySelectorAll("#datasetDropdown + .dropdown-menu .dropdown-item");
        const dropdownButton = document.getElementById("datasetDropdown");

        let selectedDropdownValue = '';

        dropdownItems.forEach(item => {
            item.addEventListener("click", function(event) {
                selectedDropdownValue = event.target.textContent;
                dropdownButton.textContent = selectedDropdownValue;
            });
        });

        const fileInput1 = document.getElementById("upload-file-1");
        const fileNameDisplay1 = document.getElementById("file-name-1");

        fileInput1.addEventListener("change", function() {
            const fileName = fileInput1.files[0] ? fileInput1.files[0].name : "No file selected";
            uploadFile(fileInput1.files[0], "file");
            fileNameDisplay1.textContent = fileName;
        });


        document.getElementById('save-button').addEventListener('click', function() {
            const filePaths = [
                document.getElementById("file-name-1").textContent, 
                document.getElementById("file-name-2").textContent, 
                document.getElementById("file-name-3").textContent, 
                document.getElementById("file-name-4").textContent,
                document.getElementById("file-name-5").textContent
            ];

            const useExisting = document.getElementById("use-existing-5").checked ? "Yes" : "No";

            console.log(filePaths, useExisting, selectedDropdownValue)

            frappe.call({
                method: "gdp_forecasting.gdp_forecasting.gdp_forecasting.upload_file",
                args: {
                    file: filePaths,
                    use_existing: useExisting,
                    dataset_type: selectedDropdownValue
                },
                callback: function(response) {
                    if (response.message) {
                        console.log('Success:', response.message);
                        setTimeout(function() {
                            window.location.href = "/forecast";
                        }, 1000);
                    } else {
                        console.log('Error in the response');
                    }
                },
                error: function(error) {
                    console.error('Error during frappe.call:', error);
                }
            });
        });

    });

    function uploadFile(file, displayId) {
        
        let formData = new FormData();
        formData.append('file', file);
        formData.append('file_name', file.name);
        formData.append('file_size', file.size);
        formData.append('attached_to_field', displayId);
        formData.append('file_url', "/private/files/" + file.name);
        formData.append('folder', "Home/Attachments"); 
        formData.append('is_private', 1);

        fetch('/api/method/upload_file', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Frappe-CSRF-Token': frappe.csrf_token
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                console.log("File uploaded successfully:", data.message.file_url);
            } else {
                console.error("Error in response:", data);
            }
        })
        .catch(error => {
            console.error("Error uploading file:", error);
        });
    }

    new WOW().init();
})(jQuery);
