/*
JaveScript functions for navigation bar

Based on example from w3schools.org, see https://www.w3schools.com/howto/howto_js_responsive_navbar_dropdown.asp
*/

/* Toggle between adding and removing the "responsive" class to topnav when the user clicks on the icon */
function toggle_navbar_menu() {
  var x = document.getElementById("main_menu");
  if (x.className === "topnav") {
    x.className += " responsive";
  } else {
    x.className = "topnav";
  }
}