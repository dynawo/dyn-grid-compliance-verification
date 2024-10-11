model VoltageRegulatorI8SM

  import Dynawo;
  
  parameter Dynawo.Types.VoltageModulePu URef0Pu "Initial control voltage in pu (base UNom)";
  parameter Dynawo.Types.VoltageModulePu U0Pu "Initial stator voltage in pu (base UNom)";
  parameter Dynawo.Types.VoltageModulePu Efd0Pu "Initial voltage output in pu (base UNom)";

  Modelica.Blocks.Interfaces.RealInput URefPu(start = URef0Pu) annotation(
    Placement(visible = true, transformation(origin = {-112, 20}, extent = {{-12, -12}, {12, 12}}, rotation = 0), iconTransformation(origin = {-112, -20}, extent = {{-12, -12}, {12, 12}}, rotation = 0)));
  Modelica.Blocks.Interfaces.RealInput UPu(start = U0Pu) annotation(
    Placement(visible = true, transformation(origin = {-112, -20}, extent = {{-12, -12}, {12, 12}}, rotation = 0), iconTransformation(origin = {-111, 21}, extent = {{-11, -11}, {11, 11}}, rotation = 0)));
  Modelica.Blocks.Math.Add add(k2 = -1)  annotation(
    Placement(visible = true, transformation(origin = {-54, 0}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Interfaces.RealOutput EfdPu(start = Efd0Pu) annotation(
    Placement(visible = true, transformation(origin = {110, 0}, extent = {{-10, -10}, {10, 10}}, rotation = 0), iconTransformation(origin = {110, -2}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Continuous.FirstOrder firstOrder(T = 0.3, k = 15)  annotation(
    Placement(visible = true, transformation(origin = {14, 0}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
equation
  connect(URefPu, add.u1) annotation(
    Line(points = {{-112, 20}, {-76, 20}, {-76, 6}, {-66, 6}}, color = {0, 0, 127}));
  connect(UPu, add.u2) annotation(
    Line(points = {{-112, -20}, {-76, -20}, {-76, -6}, {-66, -6}}, color = {0, 0, 127}));
  connect(add.y, firstOrder.u) annotation(
    Line(points = {{-42, 0}, {2, 0}}, color = {0, 0, 127}));
  connect(firstOrder.y, EfdPu) annotation(
    Line(points = {{26, 0}, {110, 0}}, color = {0, 0, 127}));
  annotation(
    uses(Modelica(version = "3.2.3"), Dynawo(version = "1.0.1")));
end VoltageRegulatorI8SM;
