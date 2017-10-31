	$("#imgInp").change(function () {
		myFunction(this);
	});
	
	document.getElementById("imgInp").change(function(){
		myFunction();
	});
	
	function myFunction() {
	document.getElementById("demo").innerHTML = "Paragraph changed.";
	var myFile = document.getElementById("imgInp");
	if (myFile.files && myFile.files.length) {
		if (typeof FileReader !== "undefined") {
			var fileReader = new FileReader();
			fileReader.onload = function(event) {
			document.getElementById("prev").src = event.target.result;
		};
		fileReader.readAsDataURL(myFile.files[0]);
		} else {
			alert("Your browser doesn't support the FileReader API.");
		}
	} else {
		alert("No file was selected.");
	}
	}