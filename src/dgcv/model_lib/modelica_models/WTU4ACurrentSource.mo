model WTU4ACurrentSource "WECC Wind Turbine model with a simplified drive train model (dual-mass model), without the plant controller and with a current source as interface with the grid"
  import Modelica;
  import Dynawo;

  extends BaseWTU4A;

  // Input variables
  Modelica.Blocks.Interfaces.RealInput PInjRefPu(start = PInj0Pu) "Active power setpoint at injector terminal in pu (generator convention) (base SNom)" annotation(
    Placement(visible = true, transformation(origin = {-190, 20}, extent = {{-10, -10}, {10, 10}}, rotation = 0), iconTransformation(origin = {-110, 60}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Interfaces.RealInput QInjRefPu(start = QInj0Pu) "Reactive power setpoint at injector terminal in pu (generator convention) (base SNom)" annotation(
    Placement(visible = true, transformation(origin = {-190, -20}, extent = {{-10, -10}, {10, 10}}, rotation = 0), iconTransformation(origin = {-110, -60}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Interfaces.RealInput VRefConst1(start = VRef1Pu) "Voltage setpoint for electrical control wind in pu (base UNom)" annotation(
    Placement(visible = true, transformation(origin = {-110, -50}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));

equation
  connect(PInjRefPu, wecc_reec.PInjRefPu) annotation(
    Line(points = {{-190, 20}, {-160, 20}, {-160, 6}, {-91, 6}}, color = {0, 0, 127}));
  connect(QInjRefPu, wecc_reec.QInjRefPu) annotation(
    Line(points = {{-190, -20}, {-160, -20}, {-160, -6}, {-91, -6}}, color = {0, 0, 127}));
  connect(VRefConst1, wecc_reec.VRefConst1) annotation(
    Line(points = {{-33, -10}, {-72, -10}, {-72, -20}, {-110, -20}}, color = {0, 0, 127}));

  annotation(
    preferredView = "diagram",
    Documentation(info = "<html><head></head><body><p> This block contains the generic WECC WT model according to (in case page cannot be found, copy link in browser): <br><a href=\"https://www.wecc.org/Reliability/WECC-Second-Generation-Wind-Turbine-Models-012314.pdf\">https://www.wecc.org/Reliability/WECC-Second-Generation-Wind-Turbine-Models-012314.pdf</a> </p>
<p> The overall model is structured as follows:
</p><ul>
<li> Main model: WECC_Wind with terminal connection and measurement inputs for P/Q/U/I.</li>
<li> Electrical inverter control.</li>
<li> Simplified drive train model, dual-mass model. </li>
<li> Generator control. </li>
<li> Injector (id,iq). </li>
</ul><div>Notice that in this model and contrary to the norm model, the plant controller is not included.</div> <p></p></body></html>"),
    Icon(graphics = {Rectangle(extent = {{-100, 100}, {100, -100}}), Text(origin = {-24, 11}, extent = {{-48, 27}, {98, -53}}, textString = "WECC WT 4A")}, coordinateSystem(initialScale = 0.1)),
    Diagram(coordinateSystem(grid = {1, 1}, extent = {{-180, -60}, {120, 60}})));
end WTU4ACurrentSource;
